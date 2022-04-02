import selectors
import struct


class Message:
    def __init__(self, selector, client_socket, client_address):
        self.selector = selector
        self.client_socket = client_socket
        self.client_address = client_address
        self._recv_buffer = b""
        self._recv_len = None
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
        pass
        if self._recv_len:
            return

        size_len = 2
        if len(self._recv_buffer) < size_len:
            return

        self._recv_len = struct.unpack(">H", self._recv_buffer[:size_len])[0]
        self._recv_buffer = self._recv_buffer[size_len:]

    def process_packet(self):
        pass

    def _read(self):
        try:
            data = self.client_socket.recv(2048)
            print(f"received {data}")
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
