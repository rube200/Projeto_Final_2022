#!/usr/bin/python
import logging
import traceback

from flup.server.fcgi import WSGIServer
from git import Git

from server import app


def main():
    try:
        logging.basicConfig(filename='server.fcgi.log', level=logging.WARNING)
        git = Git('../')
        git.pull()
    except Exception as ex:
        logging.exception(f'Exception while requesting git: {ex!r}')
        logging.exception(f'{traceback.format_exc()}')

    try:
        WSGIServer(app).run()
    except Exception as ex:
        logging.exception(f'Exception while executing wsgi server: {ex!r}')
        logging.exception(f'{traceback.format_exc()}')


if __name__ == '__main__':
    main()
