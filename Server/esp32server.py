import logging as log
from os import environ
from threading import Thread
from traceback import format_exc

from common.esp_clients import EspClients
from common.esp_events import EspEvents
from socket_server.server_socket import ServerSocket
from web.web_server import WebServer

environ['DATABASE'] = 'esp32cam.sqlite'

environ['ESP32_DEBUG'] = '1'
environ['ESP32_IP'] = '0.0.0.0'
environ['ESP32_PORT'] = '2376'

logger = False
socket_thread = None


def config_logger(filename: str = 'esp32server.py.log'):
    global logger
    if logger:
        return

    logger = True
    log.basicConfig(filename=filename, level=log.DEBUG if environ.get('ESP32_DEBUG') else log.INFO)
    log.getLogger().addHandler(log.StreamHandler())


class Esp32Server:
    def __init__(self, fcgi: bool = True):
        self.__clients = EspClients()
        self.__events = EspEvents()
        self.__fcgi = fcgi
        self.__socket_server = None
        self.__socket_thread = None
        self.__web_server = WebServer(self.__clients, self.__events)

    def __del__(self):
        if 'WERKZEUG_RUN_MAIN' in environ or self.__fcgi:
            log.info('Stopping Servers...')

        if self.__socket_server:
            self.__socket_server.shutdown()
            self.__socket_server = None

        if self.__socket_thread:
            self.__socket_thread.join()
            self.__socket_thread = None

        del self.__clients
        del self.__events
        del self.__web_server

    def run_servers(self):
        if 'WERKZEUG_RUN_MAIN' in environ or self.__fcgi:
            log.info('Running Servers...')
            self.__socket_server = ServerSocket(self.__clients, self.__events)
            self.__socket_thread = Thread(daemon=True, target=self.__socket_server.run_forever)
            self.__socket_thread.start()

        if not self.__fcgi:
            self.__web_server.run(port=80)

    @property
    def web(self) -> WebServer:
        return self.__web_server


def main():
    try:
        esp32server = Esp32Server(False)
        esp32server.run_servers()
    except Exception as ex:
        log.error(f'Exception while initializing Esp32Server: {ex!r}')
        log.error(format_exc())


if __name__ == '__main__':
    config_logger()
    main()
