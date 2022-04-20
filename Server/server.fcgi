#!/usr/bin/python
import logging as log
import traceback

from flup.server.fcgi import WSGIServer

from esp32server import config_logger, run_socket_server, set_buffer
from esp_web.flask_server import web


def main():
    try:
        config_logger('server.fcgi.log')
        set_buffer()
        run_socket_server()
        WSGIServer(web).run()
    except Exception as ex:
        log.exception(f'Exception while executing wsgi server: {ex!r}')
        log.exception(f'{traceback.format_exc()}')


if __name__ == '__main__':
    main()
