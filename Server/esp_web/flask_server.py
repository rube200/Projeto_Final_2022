import base64
import sqlite3
from flask import abort, Flask, redirect, render_template, request, send_file, url_for, stream_with_context

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

#added
@web.route('/login', methods = ['POST', 'GET'])
def login():
    if request.method == 'POST':
        usr = request.form.get('username')
        pw = request.form.get('password')
        conn = sqlite3.connect('proj.db')
        c = conn.cursor()
        c.execute("SELECT ID FROM USER WHERE NAME like ? AND PASSWORD like ?", (usr, pw))
        m = [row[0] for row in c] [0]
        return redirect(url_for("images", id = m))
    else:
        return render_template('login.html')
    



@web.route('/images/<int:id>')
def images(id):    
    conn = sqlite3.connect('proj.db')
    c = conn.cursor()
    fiveMostRecent = c.execute("SELECT DATA,DATE,ESP_NAME FROM PICTURE  WHERE USER_ID LIKE ? ORDER BY DATE desc LIMIT 5", (id,))
    #    GROUP BY USER_ID 
    #imgs = c.execute("SELECT * FROM PICTURE WHERE USER_ID LIKE ?", (id)) 
    data = []
    names = []
    dates = []
    for img in fiveMostRecent:
        data.append("data:image/png;charset=UTF-8;base64," + base64.b64encode(img[0]).decode('utf-8'))
        #data.append('iVBORw0KGgoAAAANSUhEUgAAAAoAAAAJCAIAAACExCpEAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAASSURBVChTY5DutMGDRqZ0pw0A4ZNOwQNf')
        dates.append(img[1])#.split(".")[0]) #split to remove miliseconds
        names.append(img[2])
    
    
    c.close()
    conn.close()    
    #print(data)
    return render_template('images2.html', imgs = data, dates = dates, esps = names)

#end added

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
