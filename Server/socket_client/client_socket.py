import logging as log
from selectors import BaseSelector, EVENT_READ, EVENT_WRITE
from socket import socket, SHUT_RDWR
from struct import pack
from typing import Tuple

from socket_client.client_data import ClientData
from socket_client.packet import Packet
from socket_common.packet_helper import PacketType

BINARY_ZERO = int.to_bytes(0, 4, 'big')
WRITE = EVENT_READ | EVENT_WRITE


class ClientSocket(ClientData):
    def __init__(self, address: Tuple[str, int], selector: BaseSelector, tcp_socket: socket):
        super(ClientSocket, self).__init__()
        self.__address = address
        self.__packet_read = Packet()
        self.__selector = selector
        self.__selector.register(tcp_socket, EVENT_READ, (self, self.__process_socket))
        self.__tcp_socket = tcp_socket
        self.__wait_username = False
        self.__write_buffer = b''

    def __del__(self):
        super(ClientSocket, self).__del__()
        self.__selector.unregister(self.__tcp_socket)
        self.__selector = None
        self.__tcp_socket.shutdown(SHUT_RDWR)
        self.__tcp_socket.close()
        del self.__address
        del self.__packet_read
        del self.__tcp_socket
        del self.__wait_username
        del self.__write_buffer

    def __set_mode(self, mode: int):
        self.__selector.modify(self.__tcp_socket, mode, (self, self.__process_socket))

    def __process_socket(self, events: int) -> None:
        if events & EVENT_READ:
            self.__read_socket()

        if events & EVENT_WRITE:
            self.__write_socket()

    def __process_packet(self) -> None:
        pkt_type = self.__packet_read.pkt_type
        pkt_data = self.__packet_read.pkt_data
        if pkt_type is PacketType.Uuid:
            self.__process_uuid(pkt_data)
            return

        if not self.uuid:
            log.debug(f'Receive a packet of type {pkt_type!r} from {self.__address!r} but expected a uuid!')
            return

        if pkt_type is PacketType.Username:
            self.__process_username(pkt_data)
            return

        if self.__wait_username:
            log.debug(f'Receive a packet of type {pkt_type!r} from {self.__address!r} but expected a username!')
            return

        if pkt_type is PacketType.Image:
            self.__process_camera(pkt_data)
            return

        if pkt_type is PacketType.BellPressed:
            self.__process_bell_pressed()
            return

        if pkt_type is PacketType.MotionDetected:
            self.__process_motion_detected()
            return

        raise ValueError(f'Unknown {pkt_type!r} from {self.__address!r}')

    def __process_uuid(self, data: bytes) -> None:
        self.__uuid = int(data.hex(), base=16)

    def __process_username(self, data: bytes) -> None:
        raise NotImplementedError(f'{self.__name__} does not implement __process_username')

    def __process_camera(self, data: bytes) -> None:
        self.__camera = data

    def __process_bell_pressed(self) -> None:
        raise NotImplementedError(f'{self.__name__} does not implement __process_bell_pressed')

    def __process_motion_detected(self) -> None:
        raise NotImplementedError(f'{self.__name__} does not implement __process_bell_pressed')

    def __read_socket(self) -> None:
        try:
            data = self.__tcp_socket.recv(2048)
            if not data:
                raise ConnectionResetError(104, 'Connection reset by peer.')

            self.__packet_read.append_data(data)
        except BlockingIOError as ex:
            log.warning(f'Blocking error at recv for {self.__address}: {ex!r}')

        self.__packet_read.try_get_header()
        self.__packet_read.try_get_data()
        if not self.__packet_read.is_ready():
            return

        self.__process_packet()
        self.__packet_read.reset_packet()

    def __send_config(self, config: Tuple[bool, int, int, int]) -> None:
        data = pack('>iB?iii', 13, PacketType.Config.value, config)
        self.__write_data(data)

    def __send_username_confirmation(self, valid_username: bool):
        data = pack('>iB?', 1, PacketType.Username.value, valid_username)
        self.__write_data(data)

    def __send_open_relay(self):
        self.__send_empty_packet(PacketType.OpenRelay)

    def __send_start_stream(self):
        self.__send_empty_packet(PacketType.StartStream)

    def __send_stop_stream(self):
        self.__send_empty_packet(PacketType.StopStream)

    def __send_empty_packet(self, packet_type: PacketType) -> None:
        data = pack('>iB', int(0), packet_type.value)
        self.__write_data(data)

    def __write_data(self, data: bytes) -> None:
        self.__set_mode(WRITE)
        self.__write_buffer += data

    def __write_socket(self) -> None:
        if not len(self.__write_buffer):
            self.__set_mode(EVENT_READ)
            return

        try:
            sent = self.__tcp_socket.send(self.__write_buffer)
            self.__write_buffer = self.__write_buffer[sent:]
        except BlockingIOError as ex:
            log.debug(f'Blocking error at send for {self.__address!r}: {ex!r}')

    @property
    def address(self):
        return self.__address
