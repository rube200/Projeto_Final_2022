import os
import selectors
import socket
import traceback
from threading import Thread

import pandas
from flask import Flask, render_template, request, stream_with_context, redirect, url_for

from message import Message

NAME = 'Video-Doorbell'
HOST = '0.0.0.0'
PORT = 45000

ESP = ''

app = Flask(NAME)


@app.route('/postIP', methods=['POST'])
def postIP():
    ESP = request.form.get('esp')
    if checkIP(ESP):
        print(ESP)
        return live()
        #return redirect(url_for('live'))
    print('bad ip:' ,ESP)


@app.route('/')
def selection():
    return render_template('selection.html')

@app.route('/live')
def live():
    return render_template('live.html')


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


def checkIP(ip):
    flag = False
    if ("." in ip):
        elements_array = ip.strip().split(".")
        if(len(elements_array) == 4):
            for i in elements_array:
                if not(i.isnumeric() and int(i)>=0 and int(i)<=255):
                    return False
        return True
    return False

img = b''


@app.route('/stream')
def stream():
    stream_context = stream_with_context(img)
    return app.response_class(stream_context)


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


def socket_server():
    try:
        with selectors.DefaultSelector() as selector, socket.socket() as sv_socket:
            sv_socket.bind((HOST, PORT))
            sv_socket.listen()
            sv_socket.setblocking(False)

            selector.register(sv_socket, selectors.EVENT_READ)
            print('Socket ready! Waiting connections...')
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
    except Exception as ex:
        print(f'Exception while starting socket server: {ex!r}')
        print(f'{traceback.format_exc()}')


if not os.environ.get("WERKZEUG_RUN_MAIN"):
    socket_thread = Thread(target=socket_server)
    socket_thread.start()
