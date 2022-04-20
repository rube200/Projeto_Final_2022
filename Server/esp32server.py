import logging as log
from os import environ
from threading import Thread
from traceback import format_exc

from esp_socket.socket_server import socket as socket_server
from esp_web.flask_server import web as web_server

environ['ESP32_DEBUG'] = environ['FLASK_DEBUG'] = '1'
environ['ESP32_NAME'] = 'Video-Doorbell'
environ['ESP32_IP'] = '0.0.0.0'
environ['ESP32_PORT'] = '45000'

environ['FLASK_ENV'] = 'development' if environ.get('FLASK_DEBUG') else 'production'
environ['FLASK_RUN_HOST'] = '0.0.0.0'
environ['FLASK_RUN_PORT'] = '80'

logger = False


def config_logger(filename: str = 'esp32server.py.log'):
    global logger
    if logger:
        return

    logger = True
    log.basicConfig(filename=filename, level=log.DEBUG if environ.get('ESP32_DEBUG') else log.WARNING)
    log.getLogger().addHandler(log.StreamHandler())


def run_socket_server():
    Thread(daemon=True, target=socket_server.run).start()


def run_web_server():
    web_server.run(host=environ.get('FLASK_RUN_HOST'), port=environ.get('FLASK_RUN_PORT'))


def set_buffer():
    buffer = {}
    socket_server.esp_clients = buffer
    web_server.esp_clients = buffer


def main():
    try:
        set_buffer()
        if 'WERKZEUG_RUN_MAIN' in environ:
            log.debug('Running Servers...')
            run_socket_server()
        run_web_server()

    except Exception as ex:
        log.error(f'Exception while initializing SocketServer: {ex!r}')
        log.error(format_exc())


if __name__ == '__main__':
    config_logger()
    main()
