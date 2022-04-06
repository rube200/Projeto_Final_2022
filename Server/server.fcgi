#!/usr/bin/python
import traceback

from flup.server.fcgi import WSGIServer
from git import Git

from server import app

if __name__ == '__main__':
    try:
        git = Git('../')
        git.pull()
        WSGIServer(app).run()
    except Exception as ex:
        print(f'Exception while executing wsgi server: {ex!r}')
        print(f'{traceback.format_exc()}')
