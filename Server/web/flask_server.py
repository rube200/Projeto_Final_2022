import logging as log
from collections import namedtuple
from io import BytesIO
from time import sleep, monotonic
from traceback import format_exc

import bcrypt
import jwt
from flask import abort, current_app, Flask, redirect, render_template, request, send_file, url_for, \
    stream_with_context, session, flash


class WebServer(Flask):
    def open_relay(self, esp_id):
        self.__events.on_open_relay_requested(esp_id)


def authenticate() -> (None or int):
    token = session.get('token')
    user_id = session.get('user_id')
    if not token or not user_id:
        return None

    try:
        payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], 'HS256')
        usr = payload['user_id']
        if usr != user_id:
            return None

        cursor = get_db().cursor()
        try:
            cursor.execute('SELECT username FROM user WHERE username = ?', [usr]),
            db_row = cursor.fetchone()
        finally:
            cursor.close()

        if not db_row or not db_row[0]:
            return None

        return usr

    except (jwt.ExpiredSignatureError | jwt.InvalidTokenError):
        return None


def validate_esp(esp_id: int):
    cursor = get_db().cursor()
    try:
        cursor.execute('SELECT 1 FROM doorbell WHERE id = ? and owner = ?', [esp_id, session.get('user_id')]),
        db_rows = cursor.fetchone()
        return db_rows and db_rows[0]
    finally:
        cursor.close()


@web.route('/')
def index():
    if authenticate():
        return redirect(url_for('doorbells'))

    return redirect(url_for('login'))


def redirect_to_doorbells(usr, name):
    session.permanent = True if request.form.get('keep_sign') else False
    session['token'] = get_token(usr)
    session['user_id'] = usr
    session['name'] = name or usr
    return redirect(url_for('doorbells'))


@web.route('/login', methods=['GET', 'POST'])
def login():
    if authenticate():
        return redirect(url_for('doorbells'))

    if request.method == 'GET':
        return render_template('templates/login.html')

    usr = request.form.get('username')
    pwd = request.form.get('password')
    if not usr or not pwd:
        flash('Invalid form input.', 'danger')
        return render_template('templates/login.html')

    cursor = get_db().cursor()
    try:
        cursor.execute('SELECT username, name, password FROM user WHERE username = ?', [usr]),
        db_row = cursor.fetchone()
    finally:
        cursor.close()
    if not db_row or not db_row[0] or not db_row[2] or not bcrypt.checkpw(pwd.encode('utf-8'), db_row[2]):
        flash('Invalid credentials.', 'danger')
        return render_template('templates/login.html')

    return redirect_to_doorbells(db_row[0], db_row[1])


@web.route('/register', methods=['GET', 'POST'])
def register():
    if authenticate():
        return redirect(url_for('doorbells'))

    if request.method == 'GET':
        return render_template('templates/register.html')

    usr = request.form.get('username')
    email = request.form.get('email')
    pwd = request.form.get('password')
    if not usr or not email or not pwd:
        flash('Invalid form input.', 'danger')
        return render_template('templates/register.html')

    hash_pwd = bcrypt.hashpw(pwd.encode('utf-8'), bcrypt.gensalt())

    con = get_db()
    cursor = con.cursor()
    try:
        cursor.execute('INSERT OR IGNORE INTO user (username, email, password, name) VALUES (?, ?, ?, ?)',
                       (usr, email, hash_pwd, usr))
        con.commit()
        if cursor.rowcount < 1:
            flash('Username or email already taken.', 'danger')
            return render_template('templates/register.html')

        # username sanitize
        cursor.execute('SELECT username, name FROM user WHERE username = ?', [usr])
        db_row = cursor.fetchone()
    finally:
        cursor.close()

    if not db_row or not db_row[0]:
        flash('Something went wrong, try again.', 'danger')
        return render_template('templates/register.html')

    return redirect_to_doorbells(db_row[0], db_row[1])


@web.route('/logout')
def logout():
    if not authenticate():
        return redirect(url_for('index'))

    session.permanent = False
    session.pop('user_id', None)
    session.pop('name', None)
    session.pop('token', None)
    return redirect(url_for('index'))


def get_doorbells_data():
    user_id = authenticate()
    if not user_id:
        return None

    cursor = get_db().cursor()
    try:
        cursor.execute('SELECT id, name FROM doorbell WHERE owner = ?', [user_id]),
        db_rows = cursor.fetchall()
    finally:
        cursor.close()

    bells = []
    for bell in db_rows:
        bl_id = bell[0]
        tmp_bell = namedtuple('Bell', 'id, name, image, state')
        tmp_bell.id = bl_id
        tmp_bell.name = bell[1]

        esp = web.get_client(bl_id)
        if esp:
            tmp_bell.image = esp.camera if esp.camera else url_for('static', filename='default_profile.png')
            tmp_bell.state = 'Online'
            tmp_bell.online = True
        else:
            tmp_bell.image = url_for('static', filename='default_profile.png')
            tmp_bell.state = 'Offline'
            tmp_bell.online = False
        bells.append(tmp_bell)
    return bells


@web.route('/doorbells')
def doorbells():
    bells = get_doorbells_data()
    if bells is None:
        return redirect(url_for('index'))

    return render_template('templates/doorbells.html', doorbells=bells)


@web.route('/all_streams')
def all_streams():
    bells = get_doorbells_data()
    if bells is None:
        return redirect(url_for('index'))

    return render_template('templates/all_streams.html', doorbells=bells)


@web.route('/doorbell/<int:esp_id>')
def doorbell(esp_id: int):
    # todo add this page
    pass


def generate_stream(esp_id: int):
    client = web.get_client(esp_id)
    if not client:
        return b'Content-Length: 0'

    start_at = monotonic() + 10
    client.send_start_stream(False)

    try:
        while True:
            sleep(.05)
            if not client or not client.uuid:
                client = web.get_client(esp_id)
                continue

            # noinspection PyUnboundLocalVariable
            if start_at <= monotonic():
                start_at = monotonic() + 10
                client.send_start_stream(True)

            if not client.camera:
                yield b'--frame\r\nContent-Length: 0'
                continue

            yield b'--frame\r\nContent-Length: ' + bytes(len(client.camera)) + \
                  b'\r\nContent-Type: image/jpeg\r\nTransfer-Encoding: chunked\r\n\r\n' + client.camera + b'\r\n'
    except Exception as ex:
        log.exception(f'Exception while generate_stream: {ex!r}')
        log.exception(format_exc())
    finally:
        client.send_stop_stream()
        return b'Content-Length: 0'


@web.route('/stream/<int:esp_id>')
def stream(esp_id: int):
    if not authenticate() or not validate_esp(esp_id):
        return b'Content-Length: 0'

    stream_context = stream_with_context(generate_stream(esp_id))
    return web.response_class(stream_context, mimetype='multipart/x-mixed-replace; boundary=frame')


@web.route('/<int:esp_id>/open', methods=['POST'])
def open_relay(esp_id: int):
    if not authenticate() or not validate_esp(esp_id):
        return abort(401)

    web.open_relay(esp_id)
    return '', 200


@web.route('/<int:esp_id>/image')
def image(esp_id: int):
    client = web.get_client(esp_id)
    return send_file(BytesIO(client.camera), mimetype='image/jpeg') if client else abort(400)
