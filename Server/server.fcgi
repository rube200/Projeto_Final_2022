#!/usr/bin/python
import logging as log
from traceback import format_exc

from flup.server.fcgi import WSGIServer

from esp32server import config_logger, run_socket_server, set_buffer, stop_socket_server
from esp_web.flask_server import web


def main():
    try:
        config_logger('server.fcgi.log')
        set_buffer()
        run_socket_server()
        WSGIServer(web).run()
        stop_socket_server()
    except Exception as ex:
        log.exception(f'Exception while executing wsgi server: {ex!r}')
        log.exception(format_exc())


if __name__ == '__main__':
    main()
