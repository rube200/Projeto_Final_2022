import logging as log
import struct
from enum import Enum
from selectors import EVENT_READ, EVENT_WRITE, PollSelector
from socket import socket
from traceback import format_exc
from typing import Any, Tuple, Union

Address = Union[Tuple[Any, ...], str]


class PacketType(Enum):
    RAW = 0
    STATE = 1
    IMAGE = 2


class SocketClient:
    def __init__(self, address: Address, connection: socket, selector: PollSelector, shared_dictionary: dict):
        self._address = address
        self._connection = connection
        self._shared_dictionary = shared_dictionary
        self._selector = selector

        self._camera = b''
        self._closed = False
        self._recv_buffer = b''
        self._recv_len = None
        self._recv_type = None
        self._send_buffer = b''

    def __del__(self):
        self.close()

    def __str__(self) -> str:
        return self._connection.__str__()

    @property
    def address(self):
        return self._address

    @property
    def camera(self):
        return self._camera

    def close(self):
        if self._closed:
            return

        self._closed = True

        log.info(f'Closing connection to {self._address}')
        self._selector.unregister(self._connection)
        self._connection.close()

        self._address = None
        self._connection = None
        self._selector = None

        self._recv_buffer = b''
        self._recv_len = None
        self._recv_type = None
        self._send_buffer = b''

    def process_events(self, mask):
        try:
            if mask & EVENT_READ:
                self.read()
            if mask & EVENT_WRITE:
                self.write()
        except Exception as ex:
            log.exception(f'Exception while processing event for {self.address}: {ex!r}')
            log.exception(f'{format_exc()}')
            self.close()

    def process_len(self):
        if self._recv_len:
            return

        size = 4
        if len(self._recv_buffer) < size:
            return

        self._recv_len = struct.unpack('>i', self._recv_buffer[:size])[0]
        self._recv_buffer = self._recv_buffer[size:]

    def process_packet(self):
        if not self._recv_len or not self._recv_type:
            return

        if len(self._recv_buffer) < self._recv_len:
            return

        data = self._recv_buffer[:self._recv_len]
        packet_type = PacketType(self._recv_type)

        self._recv_buffer = self._recv_buffer[self._recv_len:]
        self._recv_len = None
        self._recv_type = None

        try:
            self._process_packet(packet_type, data)
        except Exception as ex:
            log.exception(f'Exception while processing packet for {self.address}: {ex!r}')
            log.exception(f'{format_exc()}')

    def _process_packet(self, packet_type: PacketType, data: bytes):
        if packet_type is PacketType.RAW:
            print('Raw')
        elif packet_type is PacketType.STATE:
            print('State')
        elif packet_type is PacketType.IMAGE:
            log.debug(f'Received a image from {self.address}')
            self._camera = data
        else:
            print('None')

    def process_type(self):
        if not self._recv_len or self._recv_type:
            return

        size = 1
        if len(self._recv_buffer) < size:
            return

        self._recv_type = int.from_bytes(bytes=self._recv_buffer[:size], byteorder='big')
        self._recv_buffer = self._recv_buffer[size:]

    def _read(self):
        try:
            data = self._connection.recv(2048)
        except BlockingIOError:
            pass
        else:
            if data:
                self._recv_buffer += data
            else:
                raise RuntimeError('Peer closed.')

    def read(self):
        self._read()

        self.process_len()
        self.process_type()
        self.process_packet()

    def _write(self):
        if not self._send_buffer:
            return

        try:
            sent = self._connection.send(self._send_buffer)
        except BlockingIOError:
            pass
        else:
            self._send_buffer = self._send_buffer[sent:]
            if sent and not self._send_buffer:
                self.close()

    def write(self):
        self._write()
