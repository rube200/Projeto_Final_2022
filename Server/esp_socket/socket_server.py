import logging as log
import selectors
from os import environ
from socket import socket, AF_INET, SOCK_DGRAM, SOCK_STREAM
from struct import unpack
from threading import Event
from traceback import format_exc
from typing import NoReturn, Optional, Tuple

from _socket import SocketType, SHUT_RDWR, SO_KEEPALIVE, SOL_SOCKET

from esp_socket.socket_client import SocketClient
from esp_socket.socket_selector import ServerSelector, EVENT_EXCEPTIONAL


def socket_opt(sock: SocketType):
    sock.setblocking(False)
    sock.setsockopt(SOL_SOCKET, SO_KEEPALIVE, True)


class SocketServer:
    def __init__(self, esp_clients: dict = None, server_address: Tuple[str, int] = None):
        self.__esp_clients = esp_clients or {}
        self.__is_shut_down = Event()
        self.__shutdown_request = False

        if not server_address:
            ip = environ.get('ESP32_IP') or '0.0.0.0'
            port = int(environ.get('ESP32_PORT') or 45000)
            server_address = (ip, port)

        self._server_address = server_address
        self.__selector = ServerSelector()
        self.__tcp_socket = socket(AF_INET, SOCK_STREAM)
        self.__udp_socket = socket(AF_INET, SOCK_DGRAM)

    def __del__(self):  # todo
        pass

    def __accept_new_client(self) -> None:
        try:
            connection, client_address = self.__tcp_socket.accept()
            socket_opt(connection)

            SocketClient(client_address, self.__selector, connection, self.__udp_socket, self.__on_uuid_recv)
            log.info(f'Accepted a connection from {client_address!r}')

        except OSError as ex:
            log.debug(f'OS error while accepting: {ex!r}')

        except Exception as ex:
            log.error(f'Exception while accepting client: {ex!r}')
            log.error(format_exc())

    def __bind_listen(self, sock: SocketType) -> None:
        sock.bind(self._server_address)
        if sock.type is SOCK_DGRAM:
            sock.setblocking(False)
            return
        sock.listen()
        socket_opt(sock)

    def __on_uuid_recv(self, client: SocketClient) -> None:
        uuid = client.uuid
        if not uuid:
            log.warning(f'Closing client with invalid uuid: {client.address}')
            del client
            return

        if uuid in self.__esp_clients:
            # noinspection PyUnusedLocal
            cl = self.__esp_clients.pop(uuid)
            del cl

        self.__esp_clients[uuid] = client
        client.setup_client(5000, 5000)

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

    def __process_udp_request(self) -> None:
        data, client_address = self.__udp_socket.recvfrom(4086)
        if len(data) < 10:
            log.debug(f'Invalid data from {client_address!r}: {data!r}')
            return

        uuid = int(data[:6].hex(), base=16)
        data_len = unpack('>i', data[6:10])[0]
        data = data[10:]

        if not uuid or not data_len or len(data) < data_len:
            log.debug(f'Invalid data from {client_address!r}: {uuid!r} - {data_len!r} - {data!r}')
            return

        client = self.get_client(uuid)
        if not client:
            return

        client.process_udp_data(client_address, data)

    def close(self) -> None:
        self.__tcp_socket.close()
        self.__udp_socket.close()

    def prepare(self) -> None:
        try:
            self.__bind_listen(self.__tcp_socket)
            self.__bind_listen(self.__udp_socket)
            log.info(
                f'Socket ready! Tcp: {self.__tcp_socket.getsockname()!r} | Udp: {self.__udp_socket.getsockname()!r}')

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
            self.__selector.register(self.__udp_socket, selectors.EVENT_READ)
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

                    if key.fo is self.__udp_socket:
                        if mask & EVENT_EXCEPTIONAL:
                            log.warning(f'Exceptional at tcp {key!r}')

                        self.__process_udp_request()
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
