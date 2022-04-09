import logging as log
from multiprocessing.pool import ThreadPool
from selectors import BaseSelector, EVENT_READ, PollSelector
from socket import socket
from threading import Event, Thread
from traceback import format_exc

from socket_client import Address, PacketType, SocketClient


def run_socket_server(host_address: Address, debug: bool = False):
    with SocketServer(host_address, debug) as server:
        socket_thread = Thread(target=server.serve_forever)
        socket_thread.daemon = True
        socket_thread.start()


class SocketServer(socket):
    def __init__(self, host_address: Address, debug: bool = False):
        log.basicConfig(filename='socket.log', level=log.DEBUG if debug else log.WARNING)

        try:
            super().__init__()

            self._host_address = host_address
            self._selector = PollSelector
            self._shutdown_event = Event()
            self._shutdown_request = False

            self.bind(self._host_address)
            self.listen()
            self.setblocking(False)
            log.info('Socket ready!')
        except Exception as ex:
            self.close()
            log.error(f'Exception while setting up SocketServer: {ex!r}')
            log.error(format_exc())

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._shutdown_request = True
        self._shutdown_event.wait()
        super().__exit__()

    def serve_forever(self, poll_interval: float = 0.5):
        self._shutdown_event.clear()

        try:
            with self._selector() as selector, ThreadPool() as thread_pool:
                selector.register(self, EVENT_READ)
                log.info('Waiting connections...')

                while not self._shutdown_request:
                    key, mask = selector.select(poll_interval)
                    if self._shutdown_request:
                        break

                    if not key:
                        self._accept_client(selector, thread_pool)
                        return

                    data = key.data
                    try:
                        data.process_events(mask)
                    except Exception as ex:
                        log.exception(f'Exception while processing event for {data.client_address}: {ex!r}')
                        log.exception(f'{format_exc()}')
                        data.close()
        finally:
            self._shutdown_event.set()
            self._shutdown_request = False

    def _accept_client(self, selector: PollSelector, thread_pool: ThreadPool):
        try:
            connection, address = self.accept()
            log.info(f'Accepted a connection from {address}')
        except OSError:
            return

        connection.setblocking(False)
        client = SocketClient(address, connection, selector, thread_pool)
        selector.register(connection, EVENT_READ, client)

    def _process_packet(self, packet_type: PacketType, data: bytes):
        if packet_type is PacketType.RAW:
            print('Raw')
        elif packet_type is PacketType.STATE:
            print('State')
        elif packet_type is PacketType.IMAGE:
            print('Image')
            with open('test.jpeg', 'wb') as f:
                f.write(data)
        else:
            print('None')
