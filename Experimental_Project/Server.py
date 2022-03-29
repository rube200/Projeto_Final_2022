import socket

import pandas as pd
from flask import Flask, render_template

app = Flask(__name__)


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
    # Func.write('<!DOCTYPE html><body>')
    df = pd.DataFrame({
        'Days': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
        # 'Days': [['Monday', 4], ['Tuesday', 1], ['Wednesday', 2], ['Thursday', 2], ['Friday', 3], ['Saturday', 5], ['Sunday', 9]],
        'Photos': [4, 1, 2, 2, 3, 5, 9],
        'Day\'s Average': [3, 2, 3, 2, 7, 4, 1],
        # 'Colours': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday','Saturday','Sunday', 'Last Week's Average','Last Week's Average','Last Week's Average','Last Week's Average', 'This Week's Average', 'This Week's Average','This Week's Average'],
    })

    df.to_html('templates/stats.html')
    return render_template('stats.html')


def socket_server():
    s = socket.socket()

    s.bind(('0.0.0.0', 45000))
    s.listen(5)

    print('waiting clients')
    while True:
        print('accepting...')
        clt_socket, adr_socket = s.accept()
        print('accepted')
        print(clt_socket)
        print(adr_socket)

        while True:
            content = clt_socket.recv(32)
            if content:
                print(content)
            else:
                break

        print('Closing connection')
        clt_socket.close()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)
