#!/usr/bin/python3
import logging as log
from traceback import format_exc

from flup.server.fcgi import WSGIServer

from esp32server import config_logger, Esp32Server


def main():
    try:
        config_logger('server.fcgi.log')
        esp32server = Esp32Server()
        esp32server.run_servers()
        WSGIServer(esp32server.web).run()
        del esp32server
    except Exception as ex:
        log.error(f'Exception while executing wsgi server: {ex!r}')
        log.error(format_exc())


if __name__ == '__main__':
    main()
