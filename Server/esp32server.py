import logging as log
from os import environ
from threading import Thread
from traceback import format_exc

from esp_socket.socket_events import SocketEvents
from esp_socket.socket_server import sv as socket_server
from esp_web.flask_server import web as web_server

environ['ESP32_DEBUG'] = environ['FLASK_DEBUG'] = '1'
environ['ESP32_NAME'] = 'Video-Doorbell'
environ['ESP32_IP'] = '0.0.0.0'
environ['ESP32_PORT'] = '2376'

environ['FLASK_ENV'] = 'development' if environ.get('FLASK_DEBUG') else 'production'
environ['FLASK_RUN_HOST'] = '0.0.0.0'
environ['FLASK_RUN_PORT'] = '80'

environ['DATABASE'] = 'esp32cam.sqlite'

logger = False
socket_thread = None


def config_logger(filename: str = 'esp32server.py.log'):
    global logger
    if logger:
        return

    logger = True
    log.basicConfig(filename=filename, level=log.DEBUG if environ.get('ESP32_DEBUG') else log.INFO)
    log.getLogger().addHandler(log.StreamHandler())


def run_socket_server():
    global socket_thread
    socket_thread = Thread(daemon=True, target=socket_server.run_forever)
    socket_thread.start()


def run_web_server():
    web_server.run(host=environ.get('FLASK_RUN_HOST'), port=environ.get('FLASK_RUN_PORT'))


def setup_shared():
    buffer = {}
    socket_server.esp_clients = buffer
    web_server.esp_clients = buffer

    events = SocketEvents()
    socket_server.setup_events(events)
    web_server.setup_events(events)


def stop_socket_server():
    global socket_thread

    socket_server.shutdown()
    socket_server.close()
    if socket_thread:
        # noinspection PyUnresolvedReferences
        socket_thread.join()


def main():
    try:
        setup_shared()
        if 'WERKZEUG_RUN_MAIN' in environ:
            log.info('Running Servers...')
            run_socket_server()
        run_web_server()

    except Exception as ex:
        log.error(f'Exception while initializing SocketServer: {ex!r}')
        log.error(format_exc())


if __name__ == '__main__':
    config_logger()
    main()
