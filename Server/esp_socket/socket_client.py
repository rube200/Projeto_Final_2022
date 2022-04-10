import logging as log
import struct
from enum import Enum
from selectors import BaseSelector, EVENT_READ, EVENT_WRITE
from socket import socket
from traceback import format_exc
from typing import Any, Tuple, Union

Address = Union[Tuple[Any, ...], str]
BINARY_ZERO = int.to_bytes(0, 4, 'big')
WRITE = EVENT_READ | EVENT_WRITE


class PacketType(Enum):
    RAW = 0
    REQUEST_NAME = 1
    NAME = 2
    REQUEST_IMAGE = 3
    IMAGE = 4
    CLOSE_CAMERA = 5


class ClientData:
    address = None
    camera = b''
    name = None


class SocketClient:
    def __init__(self, address: Address, connection: socket, selector: BaseSelector):
        self._client_data = ClientData
        self._client_data.address = address.__str__()

        self._address = address
        self._connection = connection
        self._selector = selector

        self._closed = False
        self._recv_buffer = b''
        self._recv_len = None
        self._recv_type = None
        self._send_buffer = b''

    def __str__(self) -> str:
        return self._connection.__str__()

    @property
    def address(self):
        return self._address

    @property
    def camera(self):
        return self._client_data.camera

    @property
    def client_data(self):
        return self._client_data

    @property
    def name(self):
        return self._client_data.name or 'Video Doorbell'

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
                self._read()
            if mask & EVENT_WRITE:
                self._write()
        except Exception as ex:
            log.exception(f'Exception while processing event for {self.address}: {ex!r}')
            log.exception(f'{format_exc()}')
            self.close()

    def _get_packet_data(self):
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

    def _get_packet_len(self):
        if self._recv_len:
            return

        size = 4
        if len(self._recv_buffer) < size:
            return

        self._recv_len = struct.unpack('>i', self._recv_buffer[:size])[0]
        self._recv_buffer = self._recv_buffer[size:]

    def _get_packet_type(self):
        if not self._recv_len or self._recv_type:
            return

        size = 1
        if len(self._recv_buffer) < size:
            return

        self._recv_type = struct.unpack('>c', self._recv_buffer[:size])[0]
        self._recv_buffer = self._recv_buffer[size:]

    def _process_packet(self, packet_type: PacketType, data: bytes):
        if packet_type is PacketType.RAW:
            log.debug(f'Received a raw from {self.address}')
            return

        if packet_type is PacketType.NAME:
            log.debug(f'Received a name from {self.address}')
            self._client_data.name = data.decode('utf-8')
            return

        if packet_type is PacketType.IMAGE:
            log.debug(f'Received a image from {self.address}')
            self._client_data.camera = data
            return

        log.debug(f'Unknown {packet_type}')

    def _write_packet(self, packet_type: PacketType, data: bytes = None):
        if not packet_type:
            log.debug(f'Write packet invalid type {packet_type} for {self._address}')
            raise ValueError(f'Invalid parameter packet_type: {packet_type}')

        try:
            size = BINARY_ZERO if not data else struct.pack('>i', len(data))
            pk_type = int.to_bytes(packet_type.value, 1, 'big')

            if data:
                packet = size + pk_type + data
            else:
                packet = size + pk_type

            self._send_buffer += packet
            self._selector.modify(self._connection, WRITE, self)
        except Exception as ex:
            log.exception(f'Exception while writing packet for {self.address}: {ex!r}')
            log.exception(f'{format_exc()}')

    def requestName(self):
        self._write_packet(PacketType.REQUEST_NAME)

    def _recv(self):
        try:
            data = self._connection.recv(2048)
        except BlockingIOError as ex:
            log.debug(f'Blocking error at recv for {self._address}: {ex!r}')
        else:
            if data:
                self._recv_buffer += data
            else:
                log.debug(f'Runtime error Peer closed for {self._address}')
                raise RuntimeError('Peer closed.')

    def _read(self):
        self._recv()

        self._get_packet_len()
        self._get_packet_type()
        self._get_packet_data()

    def _write(self):
        if not self._send_buffer:
            self._selector.modify(self._connection, EVENT_READ, self)
            return

        try:
            sent = self._connection.send(self._send_buffer)
        except BlockingIOError as ex:
            log.debug(f'Blocking error at send for {self._address}: {ex!r}')
        else:
            self._send_buffer = self._send_buffer[sent:]
            if sent and not self._send_buffer:
                self._selector.modify(self._connection, EVENT_READ, self)
