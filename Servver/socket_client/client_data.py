class ClientData:
    def __init__(self):
        self._uuid = 0
        self._camera = b''

    def close(self):
        del self._uuid
        del self._camera

    @property
    def uuid(self):
        return self._uuid

    @property
    def camera(self):
        return self._camera
