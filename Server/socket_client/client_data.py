class ClientData:
    def __init__(self):
        self.__uuid = 0
        self.__camera = b''

    def __del__(self):
        del self.__uuid
        del self.__camera

    @property
    def uuid(self):
        return self.__uuid

    @property
    def camera(self):
        return self.__camera
