import logging as log
import struct
from enum import Enum
from selectors import BaseSelector, EVENT_READ, EVENT_WRITE
from socket import socket
from traceback import format_exc
from typing import Any, Tuple, Union

Address = Union[Tuple[Any, ...], str]


def wrap_try_except(func: (), msg: str = None, ex_cb: () = None):
    try:
        func()
    except Exception as ex:
        if msg:
            log.exception(f'{msg}: {ex!r}')
        else:
            log.exception(f'Exception as occurred: {ex!r}')
        log.exception(f'{format_exc()}')

        if ex_cb:
            ex_cb(ex)


class PacketType(Enum):
    RAW = 0
    STATE = 1
    IMAGE = 2


class SocketClient:
    def __init__(self, selector: BaseSelector, connection: socket, address: Address, packet_cb: ()):
        self._address = address
        self._connection = connection
        self._packet_cb = packet_cb
        self._selector = selector

        self._closed = False
        self._recv_buffer = b''
        self._recv_len = None
        self._recv_type = None
        self._send_buffer = b''

    def __del__(self):
        self.close()

    def __exit__(self, *args):
        self.close()

    def __str__(self) -> str:
        return self._connection.__str__()

    @property
    def address(self):
        return self._address

    def close(self):
        if self._closed:
            return

        self._closed = True

        log.info(f'Closing connection to {self._address}')
        wrap_try_except(lambda: self._selector.unregister(self._connection),
                        f'Exception while unregister socket for {self._address}')
        wrap_try_except(self._connection.close,
                        f'Exception while closing socket for {self._address}')

        self._address = None
        self._connection = None
        self._packet_cb = None
        self._selector = None

        self._recv_buffer = b''
        self._recv_len = None
        self._recv_type = None
        self._send_buffer = b''

    def process_events(self, mask):
        if mask & EVENT_READ:
            self.read()
        if mask & EVENT_WRITE:
            self.write()

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

        if not self.packet_recv_callback:
            log.info(f'Client {self.client_address} received a packet but don\'t have a callback to process it.')
            return

        try:
            self.packet_recv_callback(packet_type, data)
        except Exception as ex:
            log.exception(f'Exception while processing packet for {self.client_address}: {ex!r}')
            log.exception(f'{traceback.format_exc()}')

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
            data = self.client_socket.recv(2048)
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
            sent = self.client_socket.send(self._send_buffer)
        except BlockingIOError:
            pass
        else:
            self._send_buffer = self._send_buffer[sent:]
            if sent and not self._send_buffer:
                self.close()

    def write(self):
        self._write()
