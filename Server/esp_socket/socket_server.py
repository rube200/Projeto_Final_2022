import logging as log
from os import environ
from selectors import DefaultSelector, EVENT_READ
from socket import socket
from traceback import format_exc

from esp_socket.socket_client import SocketClient


class SocketServer(socket):
    def __init__(self, _esp_clients: dict = None):
        super().__init__()
        self._disposed = False
        self._esp_clients = _esp_clients or {}
        self._selector = DefaultSelector()

    def __exit__(self, *arg):
        try:
            self.close()
        except Exception as ex:
            log.error(f'Exception while exiting socket server: {ex!r}')
            log.error(format_exc())

    def __del__(self):
        try:
            self.close()
        except Exception as ex:
            log.error(f'Exception while deleting socket server: {ex!r}')
            log.error(format_exc())

    def close(self):
        if not self._disposed:
            self._disposed = True
            self._dispose()

        super().close()

    def _dispose(self):
        try:
            del self._esp_clients
            self._selector.__exit__()
            del self._selector
        except Exception as ex:
            log.error(f'Exception while disposing socket server: {ex!r}')
            log.error(format_exc())

    @property
    def esp_clients(self):
        return dict(self._esp_clients)

    @esp_clients.setter
    def esp_clients(self, value: dict):
        self._esp_clients = value

    def get_client(self, esp_id: int):
        return self._esp_clients.get(esp_id)

    def _accept_client(self):
        address = None
        try:
            connection, address = self.accept()

            client = SocketClient(address, connection, self._selector)
            client.setCloseCb(self._client_close)
            client.setUniqueIdCb(self._client_unique_id)

            log.info(f'Accepted a connection from {address}')

        except OSError as ex:
            log.debug(f'OS error while accepting {address}: {ex!r}')

        except Exception as ex:
            log.error(f'Exception while accepting client: {ex!r}')
            log.error(format_exc())

    def _client_close(self, client: SocketClient):
        if not client:
            return

        if not client.unique_id:
            del client
            return

        if self._esp_clients.get(client.unique_id) is client:
            self._esp_clients.pop(client.unique_id, None)

        del client

    def _client_unique_id(self, client: SocketClient):
        if not client:
            return

        if not client.unique_id:
            del client
            return

        cl: SocketClient = self._esp_clients.pop(client.unique_id, None)
        self._esp_clients[client.unique_id] = client

        if not cl:
            return

        del cl

    def _process_server(self):
        try:
            self._selector.register(self, EVENT_READ)
            log.info('Waiting connections...')

            while True:
                for key, mask in self._selector.select():
                    if not key.data:
                        self._accept_client()
                        continue

                    self._process_client(key.data, mask)
        except Exception as ex:
            log.error(f'Exception while processing selector: {ex!r}')
            log.error(format_exc())

    def _process_client(self, client: SocketClient, mask: int):
        try:
            client.process_events(mask)
        except Exception as ex:
            log.error(f'Exception while processing client {client.address}: {ex!r}')
            log.error(format_exc())
            self._esp_clients.pop(client.unique_id, None)
            client.close()

    def run(self):
        try:
            ip = environ.get('ESP32_IP') or '0.0.0.0'
            port = int(environ.get('ESP32_PORT') or 45000)

            self.bind((ip, port))
            self.listen()
            self.setblocking(False)
            log.info(f'Socket ready! {self.getsockname()}')
            self._process_server()

        except Exception as ex:
            log.error(f'Exception while running up SocketServer: {ex!r}')
            log.error(format_exc())


socket = SocketServer()
