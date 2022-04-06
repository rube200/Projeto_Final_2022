#!/usr/bin/python
import logging
import traceback

from flup.server.fcgi import WSGIServer
from git import Git

from server import app


def main():
    try:
        logging.basicConfig(filename='Esp32CamFcgi.log', level=logging.DEBUG)
        git = Git('../')
        logging.warning(git.working_dir)
        logging.warning(Git('~/').working_dir)
        git.pull()
        WSGIServer(app).run()
    except Exception as ex:
        logging.exception(f'Exception while executing wsgi server: {ex!r}')
        logging.exception(f'{traceback.format_exc()}')


if __name__ == '__main__':
    main()
