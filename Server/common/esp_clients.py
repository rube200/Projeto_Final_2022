from common.esp_client import EspClient


class EspClients:
    def __init__(self):
        self.__esp_clients = {}

    def __contains__(self, item):
        return item in self.__esp_clients

    def __delitem__(self, key):
        if key in self.__esp_clients:
            del self.__esp_clients[key]

    def __setitem__(self, key, value):
        self.__esp_clients[key] = value

    @property
    def esp_clients(self) -> dict:
        return dict(self.__esp_clients)

    def get_client(self, uuid: int) -> EspClient:
        return self.__esp_clients.get(uuid)
