class Buffer:
    def __init__(self):
        self._buffer = {}

    @property
    def buffer(self):
        return self._buffer

    @buffer.setter
    def buffer(self, bug: bytes):
        self._buffer = bug
