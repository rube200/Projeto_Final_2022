from struct import unpack

from socket_common.packet_helper import HEADER_SIZE, PacketType


class Packet:
    def __init__(self):
        self.__buffer = b''
        self.__data = b''
        self.__data_len = None
        self.__type = PacketType.Invalid

    def __del__(self):
        del self.__buffer
        del self.__data
        del self.__data_len
        del self.__type

    def __len__(self):
        return len(self.__buffer) + len(self.__data)

    def append_data(self, data: bytes) -> None:
        self.__buffer += data

    def try_get_header(self) -> None:
        if self.has_header():
            return

        if len(self.__buffer) < HEADER_SIZE:
            return

        self.__data_len, pkt_type = unpack('>iB', self.__buffer[:HEADER_SIZE])
        self.__type = PacketType(pkt_type)
        self.__buffer = self.__buffer[HEADER_SIZE:]

        if self.__data_len:
            return

        self.__data_len = -1

    def try_get_data(self) -> None:
        if not self.has_header() or self.is_ready() or len(self.__buffer) < self.__data_len:
            return

        self.__data = self.__buffer[:self.__data_len]
        self.__buffer = self.__buffer[self.__data_len:]

    def has_header(self) -> bool:
        return self.__type is not PacketType.Invalid

    def is_ready(self) -> bool:
        return self.has_header() and (self.__data or self.__data_len < 0)

    def reset_packet(self) -> None:
        self.__data = b''
        self.__data_len = None
        self.__type = PacketType.Invalid

    @property
    def pkt_type(self) -> PacketType:
        return self.__type

    @property
    def pkt_data(self) -> bytes:
        return self.__data
