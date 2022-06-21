import logging as log
from datetime import datetime
from multiprocessing import Event
from os import environ
from selectors import DefaultSelector, EVENT_READ
from socket import socket, AF_INET, SHUT_RDWR, SOCK_STREAM, SOL_SOCKET, SO_KEEPALIVE
from socketserver import TCPServer
from time import monotonic
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


def socket_opt(sock: socket):
    sock.setblocking(False)
    sock.setsockopt(SOL_SOCKET, SO_KEEPALIVE, True)


class ServerSocket(DatabaseAccessor):
    def __init__(self, clients: EspClients, events: EspEvents):
        super(ServerSocket, self).__init__(environ.get('DATABASE') or 'esp32cam.sqlite')
        self.__clients = clients
        self.__events = events
        self.__events.on_esp_uuid_recv += self.__on_esp_uuid_recv
        self.__events.on_esp_username_recv += self.__on_esp_username_recv
        self.__events.on_alert += self.__on_alert

        self.__selector = DefaultSelector()
        self.__server_address = get_address()
        self.__shutdown_request = False
        self.__wait_shutdown = Event()
        self.__tcp_socket = socket(AF_INET, SOCK_STREAM)
        self.__tcp_socket.bind(self.__server_address)
        socket_opt(self.__tcp_socket)
        self.__selector.register(self.__tcp_socket, EVENT_READ)

    def __del__(self):
        pass  # todo

    def __accept_new_client(self, _) -> None:
        connection = None
        try:
            connection, address = self.__tcp_socket.accept()
            socket_opt(connection)
            esp_client = EspClient(address, self.__selector, connection, self.__events)
            esp_client.send_uuid_request()
            log.info(f'Accepted a connection from {address!r}')

        except OSError as ex:
            log.debug(f'OS error while accepting: {ex!r}')
            connection.shutdown(SHUT_RDWR)
            connection.close()

        except Exception as ex:
            log.error(f'Exception while accepting client: {ex!r}')
            log.error(format_exc())
            connection.shutdown(SHUT_RDWR)
            connection.close()

    def __on_esp_uuid_recv(self, client: EspClient) -> Tuple[bool, int, int, int] or None:
        uuid = client.uuid
        if not uuid:
            log.warning(f'Closing client with invalid uuid: {client.address}')
            del client
            return None

        del self.__clients[uuid]
        owner = self._get_owner(uuid)
        if not owner:
            log.info(f'Esp32 not registered {uuid!r}')

        self.__clients[uuid] = client
        return not owner, 5000, 5000, 5000

    def __on_esp_username_recv(self, client: EspClient, username: str) -> bool:
        success = self._register_doorbell(username, client.uuid)
        if success:
            self.__events.on_alert(client.uuid, AlertType.NewBell, {})
        return success

    def __on_alert(self, uuid: int, alert_type: AlertType, info: dict) -> None:
        data = {'uuid': uuid, 'type': alert_type.value}
        if 'time' in info:
            data['time'] = datetime.fromtimestamp(info['time'])
        if 'checked' in info:
            data['checked'] = info['checked']
        if 'filename' in info:
            data['filename'] = info['filename'].lower()
        if 'notes' in info:
            data['notes'] = info['notes']

        self._add_alert(data)

    def __process_tcp(self, key, events: int) -> None:
        if not key.data:
            self.__accept_new_client(key)
            return

        client = key.data
        if not hasattr(client, 'process_socket'):
            self.__selector.unregister(key)
            log.warning(f'Selector have invalid data: {key!r}')
            return

        try:
            client.process_socket(events)
        except ConnectionResetError as ex:
            if ex.errno != 10054:
                log.error(f'Exception while processing client {client.address}: {ex!r}')
                log.error(format_exc())
            else:
                log.info(f'Client disconnect/timeout from {client.address!r}: {ex!r}')
            client.close()
            del self.__clients[client.uuid]

        except Exception as ex:
            log.error(f'Exception while processing tcp: {ex!r}')
            log.error(format_exc())
            client.close()
            del self.__clients[client.uuid]

    def run_forever(self) -> None:
        self.__tcp_socket.listen()
        log.info(f'Socket ready! Tcp: {self.__tcp_socket.getsockname()!r}')
        log.info('Waiting connections...')

        self.__shutdown_request = False
        self.__wait_shutdown.clear()
        try:
            while not self.__shutdown_request:
                ready = self.__selector.select(0.1)
                if self.__shutdown_request:
                    break

                for key, events in ready:
                    self.__process_tcp(key, events)

        finally:
            self.__wait_shutdown.set()

    def shutdown(self) -> None:
        self.__shutdown_request = True
        self.__wait_shutdown.wait()
