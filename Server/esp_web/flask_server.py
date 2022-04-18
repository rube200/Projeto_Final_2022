from flask import abort, Flask, redirect, render_template, send_file, url_for, stream_with_context

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
    def esp_clients(self):
        return dict(self._esp_clients)

    @esp_clients.setter
    def esp_clients(self, value: dict):
        self._esp_clients = value

    def get_client(self, esp_id: int):
        return self._esp_clients.get(esp_id)


web = WebServer()


@web.context_processor
def inject_nav():
    return dict(nav=NAV_DICT)


@web.errorhandler(404)
def page_not_found():
    return redirect(url_for('index'))


@web.errorhandler(400)
def invalid_request():
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
    return send_file(client.camera, mimetype='image/jpeg') if client else abort(400)


@web.route('/<int:esp_id>/live')
def live(esp_id: int):
    client = web.get_client(esp_id)
    return render_template('live.html') if client else abort(400)


@web.route('/selection')
def selection():
    esp_list = []
    with open('ESPs.txt', 'r') as fl:
        for line in fl:
            esp_list.append(line.split(','))

    door_bells = {}
    buf = web.esp_clients
    for k in buf:
        door_bells[k] = buf[k].unique_id

    return render_template('selection.html', doorbellList=door_bells)


@web.route('/stats')
def stats():
    return render_template('stats.html')


@web.route('/stream')
def stream(self, esp_id: int):
    client = web.get_client(esp_id)

    def generate():
        yield b'--frame\r\n'
        while True:
            yield b'Content-Type: image/jpeg\r\n\r\n' + client.camera + b'\r\n--frame\r\n'

    stream_context = stream_with_context(generate())
    return self.response_class(stream_context, mimetype='multipart/x-mixed-replace; boundary=frame')
