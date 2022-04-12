#!/usr/bin/python
import esp32server
import logging as log
import traceback
from flup.server.fcgi import WSGIServer


def main():
    try:
        esp32server.config_logger('server.fcgi.log')
        esp32server.run_socket_server()
        WSGIServer(esp32server.web).run()
    except Exception as ex:
        log.exception(f'Exception while executing wsgi server: {ex!r}')
        log.exception(f'{traceback.format_exc()}')


if __name__ == '__main__':
    main()
