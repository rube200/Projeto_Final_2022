import logging as log
from datetime import datetime
from multiprocessing import Event
from os import environ
from selectors import DefaultSelector, EVENT_READ
from socket import socket, AF_INET, SHUT_RDWR, SOCK_STREAM, SOL_SOCKET, SO_KEEPALIVE, SO_REUSEADDR
from traceback import format_exc
from typing import Tuple

from common.alert_type import AlertType
from common.database_accessor import DatabaseAccessor
from common.esp_client import EspClient
from common.esp_clients import EspClients
from common.esp_events import EspEvents


def get_address() -> Tuple[str, int]:
    ip = environ.get('ESP32_IP') or '0.0.0.0'
    port = int(environ.get('ESP32_PORT') or 2376)
    return ip, port


class ServerSocket(DatabaseAccessor):
    def __init__(self, clients: EspClients, events: EspEvents):
        super(ServerSocket, self).__init__(environ.get('DATABASE') or 'esp32cam.sqlite')
        self.__clients = clients
        self.__events = events
        self.__events.on_esp_uuid_recv += self.__on_esp_uuid_recv
        self.__events.on_esp_username_recv += self.__on_esp_username_recv
        self.__events.on_esp_disconnect += self.__on_esp_disconnect
        self.__events.on_alert += self.__on_alert

        self.__selector = DefaultSelector()
        self.__server_address = get_address()
        self.__shutdown_request = False
        self.__wait_shutdown = Event()
        self.__tcp_socket = socket(AF_INET, SOCK_STREAM)
        self.__tcp_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.__tcp_socket.bind(self.__server_address)
        self.__tcp_socket.setsockopt(SOL_SOCKET, SO_KEEPALIVE, True)

    def __del__(self):
        DatabaseAccessor.__del__(self)
        self.close()
        # todo may miss some code

    def close(self) -> None:
        self.__selector.unregister(self.__tcp_socket)
        self.__selector.close()

        self.__clients.close_all()

        self.__tcp_socket.shutdown(SHUT_RDWR)
        self.__tcp_socket.close()

        del self.__tcp_socket

    def __on_esp_uuid_recv(self, client: EspClient) -> Tuple[bool, int, int, int] or None:
        uuid = client.uuid
        if not uuid:
            log.warning(f'Closing client with invalid uuid: {client.address}')
            client.close()
            return None

        del self.__clients[uuid]
        owner = self._get_owner(uuid)
        if not owner:
            log.info(f'Esp32 not registered {uuid!r}')

        self.__clients[uuid] = client
        return not owner, 0, 5000, 5000

    def __on_esp_username_recv(self, client: EspClient, username: str, relay: bool) -> bool:
        success = self._register_doorbell(username, client.uuid, relay)
        if success:
            self.__events.on_alert(client.uuid, AlertType.NewBell, {})
        return success

    def __on_esp_disconnect(self, client: EspClient) -> bool:
        self.__clients.close_client(client)
        return True

    def __on_alert(self, uuid: int, alert_type: AlertType, info: dict) -> None:
        data = {'uuid': uuid, 'type': alert_type.value}
        info = info or {}
        if 'time' in info:
            data['time'] = datetime.fromtimestamp(info['time'])
        if 'checked' in info:
            data['checked'] = info['checked']
        if 'filename' in info:
            data['filename'] = info['filename'].lower()
        if 'notes' in info:
            data['notes'] = info['notes']

        self._add_alert(data)

    def run_forever(self) -> None:
        self.__selector.register(self.__tcp_socket, EVENT_READ)
        self.__tcp_socket.listen()
        log.info(f'Socket ready! Tcp: {self.__tcp_socket.getsockname()!r}')
        log.info('Waiting connections...')

        self.__shutdown_request = False
        self.__wait_shutdown.clear()
        try:
            while not self.__shutdown_request:
                ready = self.__selector.select(0.5)
                if self.__shutdown_request:
                    break

                if not ready:
                    continue

                try:
                    connection, address = self.__tcp_socket.accept()
                except Exception as ex:
                    log.error(f'Exception while accepting client: {ex!r}')
                    log.error(format_exc())
                    continue

                try:
                    connection.setsockopt(SOL_SOCKET, SO_KEEPALIVE, True)
                    connection.settimeout(1)
                    esp_client = EspClient(address, connection, self.__events)
                    esp_client.send_uuid_request()
                    log.info(f'Accepted a connection from {address!r}')

                except Exception as ex:
                    log.error(f'Exception while config client: {ex!r}')
                    log.error(format_exc())
                    connection.shutdown(SHUT_RDWR)
                    connection.close()

        finally:
            self.__wait_shutdown.set()

    def shutdown(self) -> None:
        self.__shutdown_request = True
        self.__wait_shutdown.wait()
