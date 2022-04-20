import logging as log
import struct
from enum import Enum
from selectors import BaseSelector, EVENT_READ, EVENT_WRITE
from socket import socket
from traceback import format_exc
from typing import Any, Tuple, Union

Address = Union[Tuple[Any, ...], str]
BINARY_ZERO = int.to_bytes(0, 4, 'big')
HEADER_SIZE = 5
WRITE = EVENT_READ | EVENT_WRITE


class PacketType(Enum):
    RAW = 0
    UUID = 1
    IMAGE = 2


class SocketClient:
    def __init__(self, address: Address, connection: socket, selector: BaseSelector):
        self._address = address
        self._closing_cd = None
        self._connection = connection
        self._connection.setblocking(False)
        self._selector = selector
        self._selector.register(self._connection, EVENT_READ, self)
        self._unique_id = 0
        self._unique_id_cd = None

        self._camera = b''
        self._deleted = False
        self._disposed = False
        self._name = None

        self._packet_data = b''
        self._packet_len = None
        self._packet_type = None

        self._recv_buffer = b''
        self._send_buffer = b''

        self._write_packet(PacketType.UUID)

    def __exit__(self, *arg):
        try:
            self.close()
        except Exception as ex:
            log.error(f'Exception while exiting socket server: {ex!r}')
            log.error(format_exc())

    def __del__(self):
        try:
            if self._deleted:
                return

            self._deleted = True
            self.close()
        except Exception as ex:
            log.error(f'Exception while deleting socket server: {ex!r}')
            log.error(format_exc())

    @property
    def address(self) -> Address:
        return self._address or 0

    @property
    def camera(self) -> bytes:
        return self._camera or 0

    @property
    def unique_id(self) -> int:
        return self._unique_id

    def close(self):
        if self._disposed:
            return

        self._disposed = True

        if self._closing_cd:
            self._closing_cd(self)

        try:
            del self._address

            self._connection.close()
            self._selector.unregister(self._connection)

            del self._connection
            self._selector = None

            del self._camera
            del self._name
            del self._packet_data
            del self._packet_len
            del self._packet_type
            del self._recv_buffer
            del self._send_buffer

        except Exception as ex:
            log.error(f'Exception while disposing socket server: {ex!r}')
            log.error(format_exc())

    def process_events(self, mask: int):
        if mask & EVENT_READ:
            self._read()

        if mask & EVENT_WRITE:
            self._write()

    def setCloseCb(self, fn):
        self._closing_cd = fn

    def setUniqueIdCb(self, fn):
        self._unique_id_cd = fn

    def _get_packet_header(self):
        if self._packet_type:
            return

        if len(self._recv_buffer) < HEADER_SIZE:
            return

        self._packet_len = struct.unpack('>i', self._recv_buffer[:4])[0]
        self._packet_type = int(self._recv_buffer[4])
        self._recv_buffer = self._recv_buffer[HEADER_SIZE:]

    def _get_packet_data(self):
        if not self._packet_type or self._packet_data:
            return

        if len(self._recv_buffer) < self._packet_len:
            return

        self._packet_data = self._recv_buffer[:self._packet_len]
        self._recv_buffer = self._recv_buffer[self._packet_len:]

    def _process_packet(self):
        if not self._packet_type or not self._packet_data:
            return

        data = self._packet_data
        packet_type = PacketType(self._packet_type)

        self._packet_data = b''
        self._packet_len = None
        self._packet_type = None

        if packet_type is PacketType.UUID:
            self._unique_id = int(data.hex(), base=16)
            self._name = str(self._unique_id)

            if self._unique_id_cd:
                self._unique_id_cd(self)

            return

        if packet_type is PacketType.IMAGE:
            self._camera = data
            return

        log.debug(f'Unknown {packet_type} from {self._address}')

    def _recv(self):
        try:
            data = self._connection.recv(2048)
        except BlockingIOError as ex:
            log.debug(f'Blocking error at recv for {self._address}: {ex!r}')
        except ConnectionResetError:
            pass
        else:
            if data:
                self._recv_buffer += data
            else:
                log.debug(f'Runtime error Peer closed for {self._address}')
                raise RuntimeError('Peer closed.')

    def _read(self):
        self._recv()

        self._get_packet_header()
        self._get_packet_data()
        self._process_packet()

    def _write(self):
        if not self._send_buffer:
            return

        try:
            sent = self._connection.send(self._send_buffer)
        except BlockingIOError as ex:
            log.debug(f'Blocking error at send for {self._address}: {ex!r}')
        else:
            self._send_buffer = self._send_buffer[sent:]
            if sent and not self._send_buffer:
                self._selector.modify(self._connection, EVENT_READ, self)

    def _write_packet(self, packet_type: PacketType, data: bytes = None):
        if not packet_type:
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
            log.exception(f'Exception while writing packet for {self._address}: {ex!r}')
            log.exception(f'{format_exc()}')
