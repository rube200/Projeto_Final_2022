import selectors
import struct
from enum import Enum


class PacketType(Enum):
    RAW = 0
    STATE = 1
    IMAGE = 2


SIZE_DEFAULT = 4


class Message:
    def __init__(self, selector, client_socket, client_address):
        self.selector = selector
        self.client_socket = client_socket
        self.client_address = client_address
        self._recv_buffer = b""
        self._recv_len = None
        self._recv_type = None
        self._send_buffer = b""

    def close(self):
        print(f"Closing connection to {self.client_address}")
        try:
            self.selector.unregister(self.client_socket)
        except Exception as ex:
            print(f"Exception while unregister socket for {self.client_address}: {ex!r}")

        try:
            self.client_socket.close()
        except OSError as e:
            print(f"Exception while closing socket for {self.client_address}: {e!r}")
        finally:
            self.client_socket = None

    def process_events(self, mask):
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()

    def process_len(self):
        if self._recv_len:
            return

        if len(self._recv_buffer) < SIZE_DEFAULT:
            return

        self._recv_len = struct.unpack(">i", self._recv_buffer[:SIZE_DEFAULT])[0]
        print(f"RECEIVE LEN {self._recv_len}")  # todo remove
        self._recv_buffer = self._recv_buffer[SIZE_DEFAULT:]

    def process_packet(self):
        if not self._recv_len or not self._recv_type:
            return

        if len(self._recv_buffer) < self._recv_len:
            return

        data = self._recv_buffer[:self._recv_len]
        packet_type = self._recv_type

        self._recv_buffer = self._recv_buffer[self._recv_len:]
        self._recv_len = None
        self._recv_type = None

        if packet_type is PacketType.RAW.value:
            pass
        elif packet_type is PacketType.STATE.value:
            pass
        elif packet_type is PacketType.IMAGE.value:
            pass

    def process_type(self):
        if not self._recv_len or self._recv_type:
            return

        if len(self._recv_buffer) < SIZE_DEFAULT:
            return

        self._recv_type = struct.unpack(">i", self._recv_buffer[:SIZE_DEFAULT])[0]
        print(f"RECEIVE type {self._recv_type}")  # todo remove
        self._recv_buffer = self._recv_buffer[SIZE_DEFAULT:]

    def _read(self):
        try:
            data = self.client_socket.recv(2048)
            print(f"received {len(data)}")
        except BlockingIOError:
            pass
        else:
            if data:
                self._recv_buffer += data
            else:
                raise RuntimeError("Peer closed.")

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
