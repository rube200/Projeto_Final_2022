import selectors
import struct
import socket
import traceback

HOST = "0.0.0.0"
PORT = 45000


class Message:
    def __init__(self, client_socket, client_address):
        self.client_socket = client_socket
        self.client_address = client_address
        self._recv_buffer = b""
        self._recv_len = None
        self._send_buffer = b""

    def close(self):
        print(f"Closing connection to {self.client_address}")
        try:
            selector.unregister(self.client_socket)
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


def accept_client(sv_socket):
    connection, address = sv_socket.accept()
    print(f"Accepted a connection from {address}")

    connection.setblocking(False)
    message = Message(connection, address)
    selector.register(connection, selectors.EVENT_READ, data=message)


def socket_server():
    with socket.socket() as sv_socket:
        try:
            sv_socket.bind((HOST, PORT))
            sv_socket.listen()
            sv_socket.setblocking(False)

            selector.register(sv_socket, selectors.EVENT_READ)
            print("Server ready! Waiting connections...")
            while True:
                events = selector.select()
                for key, mask in events:
                    if key.data:
                        message = key.data
                        try:
                            key.data.process_events(mask)
                        except Exception as ex:
                            print(f"Exception while processing event for {message.client_address}: {ex!r}")
                            print(f"{traceback.format_exc()}")
                            message.close()
                    else:
                        # noinspection PyTypeChecker
                        accept_client(key.fileobj)

        except KeyboardInterrupt:
            print("Caught keyboard interrupt, exiting...")


if __name__ == "__main__":
    with selectors.DefaultSelector() as selector:
        socket_server()
