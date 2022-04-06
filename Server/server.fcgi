#!/usr/bin/python
import traceback

from flup.server.fcgi import WSGIServer
from git import Repo

from server import app

if __name__ == '__main__':
    try:
        repo = Repo('')
        WSGIServer(app).run()
    except Exception as ex:
        print(f'Exception while executing wsgi server: {ex!r}')
        print(f'{traceback.format_exc()}')
