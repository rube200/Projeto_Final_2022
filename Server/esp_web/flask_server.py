from flask import Flask, redirect, url_for, render_template, send_file, stream_with_context

from buffer import Buffer
from esp_socket.socket_client import ClientData

NAV_DICT = [
    {'name': 'Home', 'image': 'home.jpg', 'url': 'index'},
    # {'name': 'Live', 'image': 'esp.png', 'url': 'live'},
    # {'name': 'Images', 'image': 'camera.png', 'url': 'images'},
    {'name': 'Stats', 'image': 'stats.png', 'url': 'stats'},
]


class WebServer(Flask):
    def __init__(self, debug: bool = False, name: str = 'Video-Doorbell'):
        super().__init__(name)
        self.debug = debug
        self.env = 'development'
        self.name = name
        self.static_url_path = '/esp32static'
        self._shared_dictionary = None

        self.add_url_rule('/', view_func=self.index)
        self.add_url_rule('/addEsp', view_func=self.addEsp)
        self.add_url_rule('/<int:esp_id>/image', view_func=self.image)
        self.add_url_rule('/<int:esp_id>/live', view_func=self.live)
        self.add_url_rule('/selection', view_func=self.selection)
        self.add_url_rule('/stats', view_func=self.stats)
        self.add_url_rule('/<int:esp_id>/stream', view_func=self.stream)

        self.context_processor(self.inject_nav)
        self.register_error_handler(404, self.page_not_found)

    def run_server(self):
        self.run(host='0.0.0.0', port=80)

    def set_shared_dict(self, shared_dictionary: Buffer):
        self._shared_dictionary = shared_dictionary

    @staticmethod
    def inject_nav():
        return dict(nav=NAV_DICT)

    @staticmethod
    def page_not_found():
        return redirect(url_for('index'))

    def index(self):
        return self.selection()

    @staticmethod
    def addEsp():  # todo
        return render_template('add.html')

    def image(self, esp_id: int):
        client: ClientData = self._shared_dictionary.buffer.get(esp_id)
        if not client:
            return self.page_not_found()

        return send_file(client.camera, mimetype='image/jpeg')

    def live(self, esp_id: int):
        client: ClientData = self._shared_dictionary.buffer.get(esp_id)
        return render_template('live.html')

    def selection(self):
        esp_list = []
        with open('ESPs.txt', 'r') as fl:
            for line in fl:
                esp_list.append(line.split(','))

        door_bells = {}
        buf = self._shared_dictionary.buffer
        for k in buf:
            door_bells[k] = buf[k].name

        return render_template('selection.html', doorbellList=door_bells)

    @staticmethod
    def stats():
        return render_template('stats.html')

    def stream(self, esp_id: int):
        client: ClientData = self._shared_dictionary.buffer.get(esp_id)

        def generate():
            yield b'--frame\r\n'
            while True:
                yield b'Content-Type: image/jpeg\r\n\r\n' + client.camera + b'\r\n--frame\r\n'

        stream_context = stream_with_context(generate())
        return self.response_class(stream_context, mimetype='multipart/x-mixed-replace; boundary=frame')
