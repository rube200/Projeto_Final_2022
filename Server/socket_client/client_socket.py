import logging as log
from selectors import BaseSelector, EVENT_READ, EVENT_WRITE
from socket import socket, SHUT_RDWR
from struct import pack
from threading import Thread
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
        self.__selector.register(tcp_socket, EVENT_READ, self)
        self.__tcp_socket = tcp_socket
        self.__wait_username = False
        self.__write_buffer = b''

    def __del__(self):
        super(ClientSocket, self).__del__()
        self.close()
        del self.__address
        del self.__packet_read
        del self.__tcp_socket
        del self.__wait_username
        del self.__write_buffer

    def close(self) -> None:
        if not self.__selector:
            return
        self.__selector.unregister(self.__tcp_socket)
        self.__selector = None
        self.__tcp_socket.shutdown(SHUT_RDWR)
        self.__tcp_socket.close()

    def __set_mode(self, mode: int):
        self.__selector.modify(self.__tcp_socket, mode, self)

    def process_socket(self, events: int) -> None:
        t = Thread(daemon=True, target=self._process_socket, args=[events])
        t.start()

    def _process_socket(self, events: int) -> None:
        if events & EVENT_READ:
            self.__read_socket()

        if events & EVENT_WRITE:
            self.__write_socket()

    def _process_packet(self) -> None:
        pkt_type = self.__packet_read.pkt_type
        pkt_data = self.__packet_read.pkt_data
        if pkt_type is PacketType.Uuid:
            self._process_uuid(pkt_data)
            return

        if not self.uuid:
            log.debug(f'Receive a packet of type {pkt_type!r} from {self.__address!r} but expected a uuid!')
            return

        if pkt_type is PacketType.Username:
            self._process_username(pkt_data)
            return

        if self.__wait_username:
            log.debug(f'Receive a packet of type {pkt_type!r} from {self.__address!r} but expected a username!')
            return

        if pkt_type is PacketType.Image:
            self._process_camera(pkt_data)
            return

        if pkt_type is PacketType.BellPressed:
            log.debug(f'Bell pressed for {self._uuid!r}')
            self._process_bell_pressed()
            return

        if pkt_type is PacketType.MotionDetected:
            log.debug(f'Movement Detected for {self._uuid!r}')
            self._process_motion_detected()
            return

        raise ValueError(f'Unknown {pkt_type!r} from {self.__address!r}')

    def _process_uuid(self, data: bytes) -> None:
        self._uuid = int(data.hex(), base=16)

    def _process_username(self, data: bytes) -> None:
        raise NotImplementedError(f'{self.__name__} does not implement __process_username')

    def _process_camera(self, data: bytes) -> None:
        self._camera = data

    def _process_bell_pressed(self) -> None:
        raise NotImplementedError(f'{self.__name__} does not implement __process_bell_pressed')

    def _process_motion_detected(self) -> None:
        raise NotImplementedError(f'{self.__name__} does not implement __process_bell_pressed')

    def __read_socket(self) -> None:
        if not self.__tcp_socket:
            return

        try:
            data = self.__tcp_socket.recv(1024)
            if not data:
                raise ConnectionResetError(104, 'Connection reset by peer.')

            self.__packet_read.append_data(data)
        except BlockingIOError as ex:
            log.warning(f'Blocking error at recv for {self.__address}: {ex!r}')

        self.__packet_read.try_get_header()
        self.__packet_read.try_get_data()
        if not self.__packet_read.is_ready():
            return

        try:
            self._process_packet()
        finally:
            self.__packet_read.reset_packet()

    def send_uuid_request(self):
        data = pack('>iB', 0, PacketType.Uuid.value)
        self.__write_data(data)

    def _send_config(self, config: Tuple[bool, int, int, int]) -> None:
        data = pack('>iB?iii', 13, PacketType.Config.value, *config)
        self.__write_data(data)

    def _send_username_confirmation(self, valid_username: bool):
        data = pack('>iB?', 1, PacketType.Username.value, valid_username)
        self.__write_data(data)

    def _send_open_relay(self):
        self.__send_empty_packet(PacketType.OpenRelay)

    def _send_start_stream(self):
        self.__send_empty_packet(PacketType.StartStream)

    def _send_stop_stream(self):
        self.__send_empty_packet(PacketType.StopStream)

    def __send_empty_packet(self, packet_type: PacketType) -> None:
        data = pack('>iB', int(0), packet_type.value)
        self.__write_data(data)

    def __write_data(self, data: bytes) -> None:
        self.__set_mode(WRITE)
        self.__write_buffer += data

    def __write_socket(self) -> None:
        if not self.__tcp_socket:
            return

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
