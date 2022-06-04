import logging as log
import selectors
from os import environ
from socket import socket, AF_INET, SOCK_STREAM
from sqlite3 import connect as sql_connect, PARSE_DECLTYPES, Row as sqlRow
from threading import Event
from traceback import format_exc
from typing import NoReturn, Optional, Tuple

from _socket import SocketType, SHUT_RDWR, SO_KEEPALIVE, SOL_SOCKET

from esp_socket.socket_client import SocketClient
from esp_socket.socket_events import SocketEvents
from esp_socket.socket_selector import ServerSelector, EVENT_EXCEPTIONAL


def socket_opt(sock: SocketType):
    sock.setblocking(False)
    sock.setsockopt(SOL_SOCKET, SO_KEEPALIVE, True)


class SocketServer:
    def __init__(self, esp_clients: dict = None, server_address: Tuple[str, int] = None):
        self.__esp_clients = esp_clients or {}
        self.__events = None
        self.__is_shut_down = Event()
        self.__shutdown_request = False

        if not server_address:
            ip = environ.get('ESP32_IP') or '0.0.0.0'
            port = int(environ.get('ESP32_PORT') or 1352)
            server_address = (ip, port)

        self.__db_config = environ.get('DATABASE') or 'esp32cam.sqlite'
        self.__selector = ServerSelector()
        self.__server_address = server_address
        self.__tcp_socket = socket(AF_INET, SOCK_STREAM)

    def setup_events(self, events: SocketEvents) -> None:
        self.__events = events
        self.__events.on_esp_uuid_recv += self.__on_uuid_recv
        self.__events.on_esp_username_recv += self.__on_username_recv
        self.__events.on_bell_pressed += self.__on_bell_pressed
        self.__events.on_motion_detected += self.__on_motion_detected

    def __get_db(self):
        sql_con = sql_connect(self.__db_config, detect_types=PARSE_DECLTYPES)
        sql_con.row_factory = sqlRow
        return sql_con

    def __accept_new_client(self) -> None:
        try:
            connection, client_address = self.__tcp_socket.accept()
            socket_opt(connection)

            SocketClient(client_address, self.__selector, connection, self.__events)
            log.info(f'Accepted a connection from {client_address!r}')

        except OSError as ex:
            log.debug(f'OS error while accepting: {ex!r}')

        except Exception as ex:
            log.error(f'Exception while accepting client: {ex!r}')
            log.error(format_exc())

    def __on_uuid_recv(self, client: SocketClient) -> Tuple[bool, int, int, int] or None:
        uuid = client.uuid
        if not uuid:
            log.warning(f'Closing client with invalid uuid: {client.address}')
            client.close()
            del client
            return None

        if uuid in self.__esp_clients:
            # noinspection PyUnusedLocal
            cl = self.__esp_clients.pop(uuid)
            cl.close()
            del cl

        con = self.__get_db()
        cursor = None
        try:
            cursor = con.cursor()
            cursor.execute('SELECT 1 FROM doorbell WHERE id = ? LIMIT 1', (uuid, ))
            data = cursor.fetchone()
            need_username = not data or not data[0]
        finally:
            if cursor:
                cursor.close()
            con.close()

        if need_username:
            log.info(f'Esp32 not registered {uuid!r}')

        self.__esp_clients[uuid] = client
        return need_username, 5000, 5000, 5000

    def __on_username_recv(self, client: SocketClient, username: str) -> bool:
        con = self.__get_db()
        cursor = None
        try:
            cursor = con.cursor()
            cursor.execute('SELECT 1 FROM user WHERE username = ? LIMIT 1', [username])
            data = cursor.fetchone()
            if not data or not data[0]:
                return False

            cursor.execute('INSERT OR IGNORE INTO doorbell(id, name, owner) VALUES (?, ?, ?)',
                           (client.uuid, client.uuid, username))
            con.commit()
            if cursor.rowcount > 0:
                return True

            cursor.execute('SELECT 1 FROM doorbell WHERE id = ? LIMIT 1', [client.uuid])
            data = cursor.fetchone()
            return data and data[0]
        finally:
            if cursor:
                cursor.close()
            con.close()

    def __add_notification_to_db(self, uuid: int, notification: int) -> None:
        con = self.__get_db()
        cursor = None
        try:
            cursor = con.cursor()
            cursor.execute('INSERT INTO notifications(esp_id, type) VALUES (?, ?)', (uuid, notification))
            con.commit()
        finally:
            if cursor:
                cursor.close()
            con.close()

    def __on_bell_pressed(self, client: SocketClient) -> None:
        self.__add_notification_to_db(client.uuid, 1)

    def __on_motion_detected(self, client: SocketClient) -> None:
        self.__add_notification_to_db(client.uuid, 2)

    def __process_exceptional(self, key) -> None:
        self.__selector.unregister(key)
        fo = key.fo
        if fo is SOCK_STREAM:
            fo.shutdown(SHUT_RDWR)

        fo.close()
        data = key.data
        if data:
            self.remove_client(data.uuid, data)
            del data

        log.warning(f'Exceptional mask detected for: {key!r}')

    def close(self) -> None:  # todo finish
        self.__tcp_socket.close()

    def prepare(self) -> None:
        try:
            self.__tcp_socket.bind(self.__server_address)
            self.__tcp_socket.listen()
            socket_opt(self.__tcp_socket)
            log.info(f'Socket ready! Tcp: {self.__tcp_socket.getsockname()!r}')

        except Exception:
            self.close()
            raise

    def run_forever(self, prepare: bool = True) -> NoReturn:
        if prepare:
            self.prepare()
        self.__shutdown_request = False
        self.__is_shut_down.clear()

        try:
            self.__selector.register(self.__tcp_socket, selectors.EVENT_READ)
            log.info('Waiting connections...')

            while not self.__shutdown_request:
                key_list = self.__selector.select(0.5)
                if self.__shutdown_request:
                    break

                for key, mask in key_list:
                    if key.fo is self.__tcp_socket:
                        if mask & EVENT_EXCEPTIONAL:
                            log.warning(f'Exceptional at tcp {key!r}')

                        self.__accept_new_client()
                        continue

                    if mask & EVENT_EXCEPTIONAL:
                        self.__process_exceptional(key)
                        continue

                    client = key.data
                    if not client:
                        self.__selector.unregister(key)
                        log.warning(f'SelectorKey have not data: {key!r}')
                        continue

                    try:
                        client.process_events(mask)

                    except ConnectionResetError as ex:
                        if ex.errno == 10054:
                            log.info(f'Client disconnect/timeout from {client.address!r}')
                            self.remove_client(client.uuid, client)
                            client.close()
                            continue

                        log.error(f'Exception while processing client {client.address}: {ex!r}')
                        log.error(format_exc())

                    except Exception as ex:
                        log.error(f'Exception while processing client {client.address}: {ex!r}')
                        log.error(format_exc())
                        self.remove_client(client.uuid, client)
                        client.close()

        finally:
            self.__is_shut_down.set()

    def shutdown(self) -> None:
        self.__shutdown_request = True
        self.__is_shut_down.wait()

    @property
    def esp_clients(self) -> dict:
        return dict(self.__esp_clients)

    @esp_clients.setter
    def esp_clients(self, value: dict):
        self.__esp_clients = value

    def get_client(self, esp_id: int) -> SocketClient:
        return self.__esp_clients.get(esp_id)

    def remove_client(self, esp_id: int, client: SocketClient = None) -> Optional[SocketClient]:
        if esp_id not in self.__esp_clients:
            if not client:
                return None

            for key, cl in self.__esp_clients:
                if cl is client:
                    return self.__esp_clients.pop(key)

            return None

        if not client:
            return self.__esp_clients.pop(esp_id)

        if self.__esp_clients[esp_id] is client:
            return self.__esp_clients.pop(esp_id)

        return None


sv = SocketServer()
