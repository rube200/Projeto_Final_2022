import logging as log
import os
from multiprocessing import Manager

from buffer import Buffer
from esp_socket.socket_server import run_socket_server
from esp_web.flask_server import WebServer

DEBUG = True
SOCKET_IP = '0.0.0.0'
SOCKET_PORT = 45000
SOCKET_HOST = (SOCKET_IP, SOCKET_PORT)

logger = False


def set_logger(name: str, debug: bool = DEBUG):
    global logger
    if logger:
        return

    logger = True
    log.basicConfig(filename=name, level=log.DEBUG if debug else log.WARNING)
    log.getLogger().addHandler(log.StreamHandler())


set_logger('server.py.log')
buf = Buffer()
web_server = WebServer(DEBUG)


def main(buf: Buffer):
    if os.environ.get('WERKZEUG_RUN_MAIN'):
        log.debug('Running Servers...')
        with Manager() as manager:
            shared_dictionary = manager.dict()
            run_socket_server(SOCKET_HOST, buf)
            web_server.set_shared_dict(buf)
    else:
        log.debug('No WERKZEUG_RUN_MAIN')
    web_server.run_server()


if __name__ == '__main__':
    main(buf)
