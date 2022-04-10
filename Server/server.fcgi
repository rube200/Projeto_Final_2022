#!/usr/bin/python
import logging as log
import traceback

from flup.server.fcgi import WSGIServer

from server import set_logger, web_server

DEBUG = True


def main():
    try:
        set_logger('server.fcgi.log', DEBUG)
        WSGIServer(web_server).run()
    except Exception as ex:
        log.exception(f'Exception while executing wsgi server: {ex!r}')
        log.exception(f'{traceback.format_exc()}')


if __name__ == '__main__':
    main()
