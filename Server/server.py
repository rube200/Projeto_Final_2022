import logging as log
import socketserver
from threading import Thread
from traceback import format_exc

import pandas
from flask import Flask, redirect, render_template, request, stream_with_context, url_for
from werkzeug.utils import secure_filename, send_file
from esp_socket.socket_server import SocketServer


SOCKET_IP = '0.0.0.0'
SOCKET_PORT = 45000
SOCKET_HOST = (SOCKET_IP, SOCKET_PORT)
SOCKET_DEBUG = True

DEBUG = True
NAME = 'Video-Doorbell'

log.basicConfig(filename='server.py.log', level=log.DEBUG if DEBUG else log.WARNING)
log.getLogger().addHandler(log.StreamHandler())

app = Flask(NAME)
app.env = 'development'
app.debug = DEBUG
app.name = 'Esp32cam-Web'
app.static_url_path = '/esp32static'

nav = [
    {'name': 'Home', 'image': 'home.jpg', 'url': 'index'},
    {'name': 'Live', 'image': 'esp.png', 'url': 'live'},
    {'name': 'Images', 'image': 'camera.png', 'url': 'images'},
    {'name': 'Stats', 'image': 'stats.png', 'url': 'stats'},
]

ESP = ''

# experimental for dynamic urls
users = {
    'johna': {
        'name': 'yef',
        'bio': 'Creator of dez nutz',
        'twitter_handle': '@johna'
    },
    'sup': {
        'name': 'mah',
        'bio': 'N',
        'twitter_handle': '@supN'
    },
    'imagine': {
        'name': 'dragon',
        'bio': 'These nuts across',
        'twitter_handle': '@your face'
    }
}


@app.route('/profile/<username>')
def profile(username):
    user = None
    if username in users:
        user = users[username]
    return render_template('user.html', username=username, user=user)


# end of dynamix url testing grounds


@app.context_processor
def inject_nav():
    return dict(nav=nav)


# noinspection PyUnusedLocal
@app.errorhandler(404)
def page_not_found(e):
    log.debug(f'Page not found {e}')
    return redirect(url_for('index'))


@app.route('/')
def index():
    log.debug('Requested index')
    return selection()


@app.route('/addESP')
def add():
    log.debug('Requested addEsp')
    return render_template('add.html')


@app.route('/image')
def image():
    log.debug('Requested image')
    filename = secure_filename('test.jpeg')
    return send_file(filename, mimetype='image/jpeg')


@app.route('/images')
def images():
    log.debug('Requested images')
    return render_template('images.html')


@app.route('/live')
def live():
    log.debug('Requested live')
    return render_template('live.html')


@app.route('/selection')
def selection():
    log.debug('Requested selection')

    esp_list = []
    with open('ESPs.txt', 'r') as fl:
        for line in fl:
            esp_list.append(line.split(','))

    return render_template('selection.html', doorbellList=esp_list)


@app.route('/stats')
def stats():
    log.debug('Requested stats')
    # Func = open('templates/stats.html','w')
    # Func.write('<!DOCTYPE html><body>\n')
    path = 'templates/stats.html'
    df = pandas.DataFrame({
        'Days': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
        # 'Days': [['Monday', 4], ['Tuesday', 1], ['Wednesday', 2], ['Thursday', 2], ['Friday', 3], ['Saturday', 5], ['Sunday', 9]],
        'Photos': [4, 1, 2, 2, 3, 5, 9],
        'Day\'s Average': [3, 2, 3, 2, 7, 4, 1],
        # 'Colours': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday','Saturday','Sunday', 'Last Week's Average','Last Week's Average','Last Week's Average','Last Week's Average', 'This Week's Average', 'This Week's Average','This Week's Average'],
    })

    html = df.to_html()
    # Func = open('templates/stats.html','a')
    # Func.write('\n<a href=\'{{ url_for('index') }}\'>Return To Homepage</a>\n</body>')
    return render_template('stats.html')


@app.route('/stream')
def stream():
    log.debug('Requested stream')

    def generate():
        yield b'--frame\r\n'
        while True:
            with open('test.jpeg', 'rb') as f:
                yield b'Content-Type: image/jpeg\r\n\r\n' + f.read() + b'\r\n--frame\r\n'

    stream_context = stream_with_context(generate())
    return app.response_class(stream_context, mimetype='multipart/x-mixed-replace; boundary=frame')


# experimental
@app.route('/postPicture', methods=['POST'])
def postPicture():
    pic = request.files('pic')
    if not pic:
        return 'No pic sent', 400

    filename = secure_filename(pic.filename)
    mimetype = pic.mimetype
    # img = Img(img=pic.read(), mimetype=mimetype, name=filename)
    # db.session.add(img)
    # db.session.commit()
    return 'Image has been uploaded', 200


@app.route('/postIP', methods=['POST'])
def postIP():
    incESP = request.form.get('esp')
    if not incESP:
        return 'No IP sent', 400
    if checkIP(incESP):
        ESP = incESP
        print(ESP)
        # return live()
        return redirect('/live')
        # return werkzeug.utils.redirect(url_for('live'))
    print('bad ip:', incESP)
    # return selection()
    return redirect(url_for('selection'))


@app.route('/postESP', methods=['POST'])
def postESP():
    name = request.form.get('name')
    ip = request.form.get('ip')
    if not name or not ip:
        return 'No ESP sent', 400
    if checkIP(ip):
        print(ip)
        f = open('ESPs.txt', 'a')
        f.write('\n' + name + ',' + ip)
        # return selection()
        return redirect('/')
    print('bad ip:', ip)
    # return selection()
    return redirect(url_for('selection'))


def checkIP(ip):
    flag = False
    if '.' in ip:
        elements_array = ip.strip().split('.')
        if len(elements_array) == 4:
            for i in elements_array:
                if not (i.isnumeric() and 0 <= int(i) <= 255):
                    return False
        return True
    return False


def _wrap_try_except(func: (), msg: str = None, ex_cb: () = None):
    try:
        func()
    except Exception as ex:
        if msg:
            log.exception(f'{msg}: {ex!r}')
        else:
            log.exception(f'Exception as occurred: {ex!r}')
        log.exception(f'{format_exc()}')

        if ex_cb:
            ex_cb(ex)


def socket_server():
    with SocketServer(SOCKET_HOST, SOCKET_DEBUG) as sv_socket:
        sv_socket.setup_server()
        sv_socket.process_server()


if __name__ == "__main__":
    socket_thread = Thread(target=_wrap_try_except, args=(socket_server, 'Exception while starting socket server'))
    socket_thread.start()
