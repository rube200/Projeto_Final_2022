from enum import Enum
from struct import unpack

HEADER_SIZE = 5


class PacketType(Enum):
    Invalid = 0
    Uuid = 1
    Config = 2
    Username = 3
    StartStream = 4
    StopStream = 5
    Image = 6
    BellPressed = 7
    MotionDetected = 8
    OpenRelay = 9


class Packet:
    def __init__(self):
        self.__buffer = b''
        self.__data = b''
        self.__data_len = None
        self.__type = PacketType.Invalid

    def __del__(self):
        self.reset_packet(True)

    def append_data(self, data: bytes) -> None:
        if not data:
            return

        self.__buffer += data

    def get_data(self) -> bytes:
        return self.__data

    def get_type(self) -> PacketType:
        return self.__type

    def is_ready_to_process(self) -> bool:
        if self.__type is PacketType.Invalid:
            return False

        if not self.__data and self.__data_len:
            return False

        return True

    def process_header(self) -> None:
        if self.__type is not PacketType.Invalid:
            self.__get_data()
            return

        if len(self.__buffer) < HEADER_SIZE:
            return

        self.__data_len, pkt_type = unpack('>iB', self.__buffer[:HEADER_SIZE])
        try:
            self.__type = PacketType(pkt_type)
        except Exception:
            print(self.__buffer)
            raise
        self.__buffer = self.__buffer[HEADER_SIZE:]
        self.__get_data()

    def __get_data(self) -> None:
        if not self.__data_len or self.__data or len(self.__buffer) < self.__data_len:
            return

        self.__data = self.__buffer[:self.__data_len]
        self.__buffer = self.__buffer[self.__data_len:]

    def reset_packet(self, clear_buffer: bool) -> None:
        if clear_buffer:
            self.__buffer = b''
        self.__data = b''
        self.__data_len = None
        self.__type = PacketType.Invalid
