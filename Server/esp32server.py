import logging as log
from os import environ

# from multiprocessing import Manager

environ['DEBUG'] = '1'
environ['ESP32_IP'] = '0.0.0.0'
environ['ESP32_PORT'] = '45000'

buffer = {}
logger = False
socket = SocketServer(buffer)
web = WebServer(buffer)


def config_logger(filename: str = 'esp32server.py.log'):
    global logger
    if logger:
        return

    logger = True
    log.basicConfig(filename=filename, level=log.DEBUG if environ.get('DEBUG') else log.WARNING)
    log.getLogger().addHandler(log.StreamHandler())


def run_socket_server():
    socket.run_forever()


def run_web_server():
    web.run_forever()


def main():
    if 'WERKZEUG_RUN_MAIN' not in environ:
        log.debug('Running Servers...')
        run_socket_server()
    run_web_server()


if __name__ == '__main__':
    config_logger()
    main()
