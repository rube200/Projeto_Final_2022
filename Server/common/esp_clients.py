from threading import Lock
from typing import Dict

from common.esp_client import EspClient


class EspClients:
    def __init__(self):
        self.__esp_clients = {}
        self.__lock = Lock()

    def __contains__(self, item):
        self.__lock.acquire()
        try:
            return item in self.__esp_clients
        finally:
            self.__lock.release()

    def __delitem__(self, key: int):
        self.__lock.acquire()
        try:
            if key in self.__esp_clients:
                self.__esp_clients.pop(key).close()
        finally:
            self.__lock.release()

    def __setitem__(self, key: int, value: EspClient):
        self.__lock.acquire()
        try:
            if key not in self.__esp_clients:
                self.__esp_clients[key] = value
                return

            cl = self.__esp_clients[key]
            if cl == value:
                return

            self.__esp_clients.pop(key).close()
            self.__esp_clients[key] = value
        finally:
            self.__lock.release()

    def close_client(self, client: EspClient) -> None:
        self.__lock.acquire()
        try:
            uuid = client.uuid
            if not uuid or uuid not in self.__esp_clients:
                client.close()
                return

            cl = self.__esp_clients[uuid]
            if cl != client:
                client.close()
                return

            self.__esp_clients.pop(uuid).close()
        finally:
            self.__lock.release()

    def close_all(self) -> None:
        self.__lock.acquire()
        try:
            for key in self.__esp_clients:
                self.__esp_clients.pop(key).close()
        finally:
            self.__lock.release()

    @property
    def esp_clients(self) -> Dict[int, EspClient]:
        return dict(self.__esp_clients)

    def get_client(self, uuid: int) -> EspClient:
        return self.__esp_clients.get(uuid)
