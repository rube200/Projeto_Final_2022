import logging as log
from concurrent.futures.thread import ThreadPoolExecutor
from selectors import BaseSelector, DefaultSelector, EVENT_READ
from socket import socket
from threading import Event, Thread
from traceback import format_exc

from buffer import Buffer
from esp_socket.socket_client import Address, SocketClient


def run_socket_server(host_address: Address, shared_dictionary: Buffer):
    socket_thread = Thread(target=_run_socket_server, args=(host_address, shared_dictionary))
    socket_thread.daemon = True
    socket_thread.start()


def _run_socket_server(host_address: Address, shared_dictionary: Buffer):
    try:
        with DefaultSelector() as selector, ThreadPoolExecutor() as thread_pool, SocketServer(host_address, selector,
                                                                                              shared_dictionary,
                                                                                              thread_pool) as server:
            server.serve_forever()
    except Exception as ex:
        log.error(f'Exception while initializing SocketServer: {ex!r}')
        log.error(format_exc())


class SocketServer(socket):
    def __init__(self, host_address: Address, selector: BaseSelector, shared_dictionary: Buffer,
                 thread_pool: ThreadPoolExecutor):
        try:
            super().__init__()
            self._client_id = 0
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
            self._shutdown_request = True
            self.close()
            log.error(f'Exception while setting up SocketServer: {ex!r}')
            log.error(format_exc())

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._shutdown_request = True
        self._shutdown_event.wait()
        super().__exit__()

    def serve_forever(self):
        if self._shutdown_request:
            return

        self._shutdown_event.clear()
        try:
            self._selector.register(self, EVENT_READ)
            log.info('Waiting connections...')

            while not self._shutdown_request:
                for key, mask in self._selector.select():
                    if self._shutdown_request:
                        break

                    if not key.data:
                        self._accept_client()
                        continue

                    self._thread_pool.submit(key.data.process_events, mask)
        except Exception as ex:
            log.error(f'Exception while processing selector: {ex!r}')
            log.error(format_exc())

        finally:
            self._shutdown_event.set()
            self._shutdown_request = False

    def _accept_client(self):
        address = None
        try:
            connection, address = self.accept()
            self._client_id += 1
            log.info(f'Accepted a connection from {address} - Id: {self._client_id}')

            connection.setblocking(False)
            client = SocketClient(address, connection, self._selector)
            self._selector.register(connection, EVENT_READ, client)
            self._shared_dictionary.buffer[self._client_id] = client.client_data
            client.requestName()

        except OSError as ex:
            log.debug(f'OS error while accepting {address}: {ex!r}')

        except Exception as ex:
            log.error(f'Exception while accepting client: {ex!r}')
            log.error(format_exc())
