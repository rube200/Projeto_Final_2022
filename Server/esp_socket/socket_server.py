import logging as log
from concurrent.futures.thread import ThreadPoolExecutor
from selectors import EVENT_READ, PollSelector
from socket import socket
from threading import Event, Thread
from traceback import format_exc

from socket_client import Address, SocketClient


def run_socket_server(host_address: Address, shared_dictionary: dict, debug: bool = False):
    socket_thread = Thread(target=_run_socket_server, args=(host_address, shared_dictionary, debug, ...))
    socket_thread.daemon = True
    socket_thread.start()


def _run_socket_server(host_address: Address, shared_dictionary: dict, thread_pool: ThreadPoolExecutor,
                       debug: bool = False):
    with PollSelector() as selector, SocketServer(host_address, selector, shared_dictionary, thread_pool,
                                                  debug) as server:
        server.serve_forever()


class SocketServer(socket):
    def __init__(self, host_address: Address, selector: PollSelector, shared_dictionary: dict,
                 thread_pool: ThreadPoolExecutor, debug: bool = False):
        log.basicConfig(filename='socket.log', level=log.DEBUG if debug else log.WARNING)

        try:
            super().__init__()

            self._host_address = host_address
            self._selector = selector
            self._shared_dictionary = shared_dictionary
            self._shutdown_event = Event()
            self._shutdown_request = False
            self._thread_pool = thread_pool

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
            self._selector.register(self, EVENT_READ)
            log.info('Waiting connections...')

            while not self._shutdown_request:
                key, mask = self._selector.select(poll_interval)
                if self._shutdown_request:
                    break

                if not key:
                    self._accept_client()
                    return

                self._thread_pool.submit(key.data.process_events, mask)

        finally:
            self._shutdown_event.set()
            self._shutdown_request = False

    def _accept_client(self):
        try:
            connection, address = self.accept()
            log.info(f'Accepted a connection from {address}')
        except OSError:
            return

        connection.setblocking(False)
        client = SocketClient(address, connection, self._selector, self._shared_dictionary)
        self._selector.register(connection, EVENT_READ, client)
