import io
import logging
import os
import selectors
import socket
import time
import traceback
from threading import Thread

import pandas
from flask import Flask, redirect, render_template, request, stream_with_context, url_for
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from message import Message, PacketType

# from db import db_init, db
# from models import Img

DEBUG = True
NAME = 'Video-Doorbell'
HOST = '0.0.0.0'
PORT = 45000

logging.basicConfig(filename='server.py.log', level=logging.DEBUG if DEBUG else logging.WARNING)
logging.getLogger().addHandler(logging.StreamHandler())

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
    logging.debug(f'Page not found {e}')
    return redirect(url_for('index'))


@app.route('/')
def index():
    logging.debug('Requested index')
    return selection()


@app.route('/addESP')
def add():
    logging.debug('Requested addEsp')
    return render_template('add.html')


@app.route('/images')
def images():
    logging.debug('Requested images')
    return render_template('images.html')


@app.route('/live')
def live():
    logging.debug('Requested live')
    return render_template('live.html')


@app.route('/selection')
def selection():
    logging.debug('Requested selection')

    esp_list = []
    with open('ESPs.txt', 'r') as fl:
        for line in fl:
            esp_list.append(line.split(','))

    return render_template('selection.html', doorbellList=esp_list)


@app.route('/stats')
def stats():
    logging.debug('Requested stats')
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
    logging.debug('Requested stream')

    def generate():
        with open('test.jpeg', 'rb') as f:
            for row in f:
                yield row

    stream_context = stream_with_context(generate())
    return app.response_class(stream_context)


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


def accept_socket_client(selector, sv_socket):
    try:
        connection, address = sv_socket.accept()
        logging.info(f'Accepted a connection from {address}')

        connection.setblocking(False)
        message = Message(selector, connection, address, packet_recv_callback)
        selector.register(connection, selectors.EVENT_READ, data=message)
    except Exception as ex:
        logging.exception(f'Exception while accepting new socket client: {ex!r}')
        logging.exception(f'{traceback.format_exc()}')


def packet_recv_callback(packet_type: PacketType, data: bytes):
    if packet_type is PacketType.RAW:
        print('Raw')
    elif packet_type is PacketType.STATE:
        print('State')
    elif packet_type is PacketType.IMAGE:
        start_time = time.time()
        file_name = secure_filename('test.jpeg')
        with open(file_name, 'wb') as f:
            f.write(data)

        # file = FileStorage(io.BytesIO(data), )
        # file.save(file_name, len(data))
        print('--- %s seconds ---' % (time.time() - start_time))
        print('Image')
    else:
        print('None')
    pass


def socket_server():
    try:
        with selectors.DefaultSelector() as selector, socket.socket() as sv_socket:
            sv_socket.bind((HOST, PORT))
            sv_socket.listen()
            sv_socket.setblocking(False)

            selector.register(sv_socket, selectors.EVENT_READ)
            logging.info('Socket ready! Waiting connections...')
            while True:
                events = selector.select()
                for key, mask in events:
                    if key.data:
                        message = key.data
                        try:
                            key.data.process_events(mask)
                        except Exception as ex:
                            logging.exception(f'Exception while processing event for {message.client_address}: {ex!r}')
                            logging.exception(f'{traceback.format_exc()}')
                            message.close()
                    else:
                        # noinspection PyTypeChecker
                        accept_socket_client(selector, key.fileobj)
    except Exception as ex:
        logging.exception(f'Exception while starting socket server: {ex!r}')
        logging.exception(f'{traceback.format_exc()}')


if not os.environ.get('WERKZEUG_RUN_MAIN'):
    socket_thread = Thread(target=socket_server)
    socket_thread.start()
