import logging as log
from socket import socket, SHUT_RDWR
from struct import pack
from typing import Any, Callable, Tuple

from esp_socket.socket_packet import Packet, PacketType
from esp_socket.socket_selector import BaseSelector, EVENT_EXCEPTIONAL, EVENT_READ, EVENT_WRITE

BINARY_ZERO = int.to_bytes(0, 4, 'big')
READ = EVENT_READ | EVENT_EXCEPTIONAL
WRITE = READ | EVENT_WRITE


class SocketClient(Packet):
    def __init__(self, address: Tuple[str, int], selector: BaseSelector, tcp_socket: socket,
                 uuid_cb: Callable[[Any], None], username_cb: Callable[[Any, str], bool]):
        super(SocketClient, self).__init__()
        self.__address = address
        self.__selector = selector
        self.__tcp_socket = tcp_socket
        self.__uuid_cb = uuid_cb
        self.__username_cb = username_cb

        self.__bell_pressed = False
        self.__motion_detected = False
        self.__camera = b''
        self.__selector.register(self.__tcp_socket, READ, self)
        self.__uuid = 0
        self.__wait_username = False
        self.__write_buffer = b''

    def close(self) -> None:
        self.reset_packet(True)
        self.__address = None
        self.__bell_pressed = False
        self.__camera = None
        self.__motion_detected = False
        self.__selector.unregister(self.__tcp_socket)
        self.__selector = None
        self.__tcp_socket.shutdown(SHUT_RDWR)
        self.__tcp_socket.close()
        self.__tcp_socket = None
        self.__uuid = 0
        self.__uuid_cb = None
        self.__username_cb = None
        self.__wait_username = False
        self.__write_buffer = None

    def __recv(self) -> None:
        try:
            data = self.__tcp_socket.recv(2048)
            if not data:
                raise ConnectionResetError(104, 'Connection reset by peer.')

            self.append_data(data)

        except BlockingIOError as ex:
            log.warning(f'Blocking error at recv for {self.__address}: {ex!r}')

    def __process_recv(self) -> None:
        self.process_header()
        if not self.is_ready_to_process():
            return

        try:
            self.__process_packet()
        finally:
            self.reset_packet(False)

    def __process_packet(self) -> None:
        pkt_type = self.get_type()
        if pkt_type is PacketType.Uuid:
            self.__process_uuid(self.get_data())
            return

        if not self.__uuid:
            log.debug(f'Receive a packet of type {pkt_type!r} from {self.__address!r} but expected a uuid!')
            return

        if pkt_type is PacketType.Username:
            self.__process_username(self.get_data())
            return

        if self.__wait_username:
            log.debug(f'Receive a packet of type {pkt_type!r} from {self.__address!r} but expected a username!')
            return

        if pkt_type is PacketType.Image:
            self.__camera = self.get_data()
            return

        if pkt_type is PacketType.BellPressed:
            self.__bell_pressed = True
            return

        if pkt_type is PacketType.MotionDetected:
            self.__motion_detected = True
            return

        raise ValueError(f'Unknown {pkt_type!r} from {self.__address!r}')

    def __process_uuid(self, data: bytes) -> None:
        self.__uuid = int(data.hex(), base=16)
        self.__uuid_cb(self)

    def __process_username(self, data: bytes) -> None:
        username = data.decode('utf-8')
        valid = self.__username_cb(self, username)
        self.__send_username_confirmation(valid)

    def __write(self) -> None:
        if not self.__write_buffer:
            self.__selector.modify(self.__tcp_socket, READ, self)
            return

        try:
            sent = self.__tcp_socket.send(self.__write_buffer)
            self.__write_buffer = self.__write_buffer[sent:]
            if not self.__write_buffer:
                self.__selector.modify(self.__tcp_socket, EVENT_READ, self)

        except BlockingIOError as ex:
            log.debug(f'Blocking error at send for {self.__address!r}: {ex!r}')

    def __write_data(self, data: bytes) -> None:
        self.__write_buffer += data
        self.__selector.modify(self.__tcp_socket, WRITE, self)

    def process_events(self, mask: int) -> None:
        if mask & EVENT_READ:
            self.__recv()
            self.__process_recv()

        if mask & EVENT_WRITE:
            self.__write()

    def __send_config(self, need_username: bool, bell_duration: int, motion_duration: int, relay_duration: int) -> None:
        data = pack('>iB?iii', 13, PacketType.Config.value, need_username, bell_duration, motion_duration,
                    relay_duration)
        # 13 is 1(bool) 12(3 * 4(int)) size
        self.__write_data(data)

    def __send_username_confirmation(self, valid_username: bool):
        data = pack('>iB?', 1, PacketType.Username.value, valid_username)
        self.__write_data(data)

    def send_start_stream(self) -> None:
        self.__send_empty_packet(PacketType.StartStream)

    def send_stop_stream(self) -> None:
        self.__send_empty_packet(PacketType.StopStream)

    def open_relay(self) -> None:
        self.__send_empty_packet(PacketType.OpenRelay)

    def __send_empty_packet(self, packet_type: PacketType) -> None:
        data = pack('>iB', int(0), packet_type.value)
        self.__write_data(data)

    def setup_client(self, need_username: bool, bell_duration: int, motion_duration: int, relay_duration: int) -> None:
        self.__wait_username = need_username
        self.__send_config(need_username, bell_duration, motion_duration, relay_duration)

    @property
    def address(self) -> Tuple[str, int]:
        return self.__address

    @property
    def camera(self) -> bytes:
        return self.__camera

    @property
    def uuid(self) -> int:
        return self.__uuid

    def peek_bell_pressed(self) -> bool:
        if not self.__bell_pressed:
            return False

        self.__bell_pressed = False
        return True
