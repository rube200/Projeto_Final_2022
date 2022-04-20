import logging
from io import BytesIO
from time import sleep

from flask import abort, Flask, redirect, render_template, send_file, url_for, stream_with_context

from esp_socket.socket_client import SocketClient

NAV_DICT = [
    {'name': 'Home', 'image': 'home.jpg', 'url': 'index'},
    # {'name': 'Live', 'image': 'esp.png', 'url': 'live'},
    # {'name': 'Images', 'image': 'camera.png', 'url': 'images'},
    {'name': 'Stats', 'image': 'stats.png', 'url': 'stats'},
]


class WebServer(Flask):
    def __init__(self, _esp_clients: dict = None):
        super().__init__(import_name=__name__, static_url_path='/esp32static')
        self._esp_clients = _esp_clients or {}

    @property
    def esp_clients(self) -> dict:
        return dict(self._esp_clients)

    @esp_clients.setter
    def esp_clients(self, value: dict):
        self._esp_clients = value

    def get_client(self, esp_id: int) -> SocketClient:
        return self._esp_clients.get(esp_id)


web = WebServer()


@web.context_processor
def inject_nav():
    return dict(nav=NAV_DICT)


# noinspection PyUnusedLocal
@web.errorhandler(404)
def page_not_found(e):
    return redirect(url_for('index'))


# noinspection PyUnusedLocal
@web.errorhandler(400)
def invalid_request(e):
    return redirect(url_for('index'))


@web.route('/')
def index():
    return selection()


@web.route('/addEsp')
def addEsp():
    return render_template('add.html')


@web.route('/<int:esp_id>/image')
def image(esp_id: int):
    client = web.get_client(esp_id)
    return send_file(BytesIO(client.camera), mimetype='image/jpeg') if client else abort(400)


@web.route('/<int:esp_id>/live')
def live(esp_id: int):
    client = web.get_client(esp_id)
    return render_template('live.html', esp_id=esp_id) if client else abort(400)


@web.route('/selection')
def selection():
    return render_template('selection.html', doorbells=web.esp_clients)


@web.route('/stats')
def stats():
    return render_template('stats.html')


@web.route('/<int:esp_id>/stream')
def stream(esp_id: int):
    client = web.get_client(esp_id)

    def generate():
        try:
            cl = client
            while True:
                if cl:
                    yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + cl.camera + b'\r\n'
                else:
                    cl = web.get_client(esp_id)

                sleep(.05)

        finally:
            logging.warning("Exiting stream")

    stream_context = stream_with_context(generate())
    return web.response_class(stream_context, mimetype='multipart/x-mixed-replace; boundary=frame')
