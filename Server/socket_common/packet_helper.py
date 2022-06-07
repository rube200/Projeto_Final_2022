from enum import Enum

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
