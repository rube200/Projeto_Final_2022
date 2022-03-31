import os
import selectors
import socket
import traceback
from threading import Thread

import pandas
from flask import Flask, render_template

from message import Message

NAME = 'Video-Doorbell'
HOST = '0.0.0.0'
PORT = 45000

app = Flask(NAME)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/client')
def client():
    return render_template('client.html')


@app.route('/images')
def images():
    return render_template('images.html')


@app.route('/stats')
def stats():
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
    pass


def accept_socket_client(selector, sv_socket):
    try:
        connection, address = sv_socket.accept()
        print(f'Accepted a connection from {address}')

        connection.setblocking(False)
        message = Message(selector, connection, address)
        selector.register(connection, selectors.EVENT_READ, data=message)
    except Exception as ex:
        print(f'Exception while accepting new socket client: {ex!r}')
        print(f'{traceback.format_exc()}')


def socket_server(selector):
    while True:
        events = selector.select()
        for key, mask in events:
            if key.data:
                message = key.data
                try:
                    key.data.process_events(mask)
                except Exception as ex:
                    print(f'Exception while processing event for {message.client_address}: {ex!r}')
                    print(f'{traceback.format_exc()}')
                    message.close()
            else:
                # noinspection PyTypeChecker
                accept_socket_client(selector, key.fileobj)


def start_socket_server():
    try:
        with selectors.DefaultSelector() as selector, socket.socket() as sv_socket:
            sv_socket.bind((HOST, PORT))
            sv_socket.listen()
            sv_socket.setblocking(False)

            selector.register(sv_socket, selectors.EVENT_READ)
            print('Socket ready! Waiting connections...')
            socket_server(selector)
    except Exception as ex:
        print(f'Exception while starting socket server: {ex!r}')
        print(f'{traceback.format_exc()}')


if __name__ == '__main__' and not os.environ.get('WERKZEUG_RUN_MAIN'):
    socket_thread = Thread(target=start_socket_server)
    socket_thread.start()
    app.run(debug=True, host='0.0.0.0', port=80)
