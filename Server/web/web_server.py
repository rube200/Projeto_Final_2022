import logging as log
from collections import namedtuple
from os import environ
from time import monotonic, sleep

import bcrypt
import jwt
from flask import Flask, redirect, url_for, current_app, abort, session, render_template, request, flash, \
    stream_with_context
from flask_mail import Mail, Message

from common.database_accessor import DatabaseAccessor
from common.esp_client import EspClient
from common.esp_clients import EspClients
from common.esp_events import EspEvents
from common.notification_type import NotificationType

NAV_DICT = [
    {'id': 'doorbells', 'title': 'Manage Doorbells', 'icon': 'bi-book-fill', 'url': 'doorbells'},
    {'id': 'all_streams', 'title': 'All Streams', 'icon': 'bi-cast', 'url': 'all_streams'},
    {'id': 'notifications', 'title': 'Notifications', 'icon': 'bi-bell-fill', 'url': 'notifications'},
    {'id': 'statistics', 'title': 'Statistics', 'icon': 'bi-bar-chart-fill', 'url': 'doorbells'},
]


def redirect_after_auth(username: str, name: str):
    session['token'] = jwt.encode({'username': username}, current_app.config['JWT_SECRET_KEY'], 'HS256')
    session['user_id'] = username
    session['user_name'] = name
    return redirect(url_for('doorbells'))


def endpoint_logout():
    session.clear()
    return redirect(url_for('index'))


class WebServer(DatabaseAccessor, Flask):
    def __init__(self, clients: EspClients, events: EspEvents):
        DatabaseAccessor.__init__(self, environ.get('DATABASE') or 'esp32cam.sqlite')
        Flask.__init__(self, __name__)

        self.__clients = clients
        self.__events = events
        self.__events.on_notification += self.__on_notification
        self.config.from_pyfile('flask.cfg')

        if self.config.get('RANDOM_SECRET_KEY'):
            import secrets
            self.config['JWT_SECRET_KEY'] = secrets.token_hex(32)
            self.config['SECRET_KEY'] = secrets.token_hex(32)
        self.__mail = Mail(self)
        self.__setup_db()
        self.__setup_web()

    def __setup_db(self):
        con = self.__get_connection()
        cursor = con.cursor()

        with current_app.open_resource(current_app.config['SCHEMA_FILE']) as f:
            cursor.executescript(f.read().decode('utf-8'))
        con.commit()

        cursor.close()
        con.close()

    def __setup_web(self):
        self.add_url_rule('/', 'index', self.__endpoint_index)
        self.add_url_rule('/login', 'login', self.__endpoint_login, methods=['GET', 'POST'])
        self.add_url_rule('/register', 'register', self.__endpoint_register, methods=['GET', 'POST'])
        self.add_url_rule('/logout', 'logout', endpoint_logout)
        self.add_url_rule('/doorbells', 'doorbells', self.__endpoint_doorbells)
        self.add_url_rule('/all_streams', 'all_streams', self.__endpoint_all_streams)
        self.add_url_rule('/stream/<int:uuid>', 'stream', self.__endpoint_esp_stream)
        self.add_url_rule('/open_doorbell/<int:uuid>', 'open_doorbell', self.__endpoint_open_doorbell)
        self.register_error_handler(400, lambda e: redirect(url_for('index')))
        self.register_error_handler(404, lambda e: redirect(url_for('index')))
        self.template_context_processors[None].append(lambda: dict(nav=NAV_DICT))

    def __authenticate(self):
        token = session.get('token')
        if not token:
            return None

        try:
            payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], 'HS256')
            username = payload['username']
            if not username:
                return None
        except (jwt.ExpiredSignatureError | jwt.InvalidTokenError):
            return None

        data = self.__get_user_by_username(username)
        session['user_id'] = username = data[0]
        session['user_name'] = data[1]
        return username

    def __get_doorbells(self):
        username = self.__authenticate()
        if not username:
            return None

        data = self.__get_doorbells_by_owner(username)
        if not data:
            return []

        bells = []
        for bell_data in data:
            tmp_bell = namedtuple('Bell', 'id, name, image, state')
            tmp_bell.id = bell_data[0]
            tmp_bell.name = bell_data[1]

            esp = self.__clients.get_client(tmp_bell.id)
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

    def __generate_stream(self, uuid: int):
        esp = self.__clients.get_client(uuid)
        if not esp:
            return b'Content-Length: 0'

        start_at = monotonic() + 10
        self.__events.on_start_stream_requested(uuid, False)
        try:
            while True:
                sleep(.05)
                if not esp or not esp.uuid:
                    esp = self.__clients.get_client(uuid)
                    continue

                # noinspection PyUnboundLocalVariable
                if start_at <= monotonic():
                    start_at = monotonic() + 10
                    self.__events.on_start_stream_requested(uuid, True)

                camera = self.__events.on_camera_requested(uuid)
                if not camera:
                    yield b'--frame\r\nContent-Length: 0'
                    continue

                yield b'--frame\r\nContent-Length: ' + bytes(len(camera)) + \
                      b'\r\nContent-Type: image/jpeg\r\nTransfer-Encoding: chunked\r\n\r\n' + camera + b'\r\n'
        finally:
            self.__events.on_stop_stream_requested(uuid)
            return b'Content-Length: 0'

    def __on_notification(self, client: EspClient, notification_type: NotificationType, _):
        try:
            email = self.__get_owner_email(client.uuid)
            if not email:
                return

            self.__mail.send(
                Message('Doorbell pressed' if notification_type is NotificationType.Bell else 'Motion detected',
                        [email],
                        'GOT CHECK IT NOW. MOTHERFUCKER'))
        except Exception as ex:
            log.error(f'Exception while getting email for esp_id {client.uuid}: {ex!r}')

    def __endpoint_index(self):
        if self.__authenticate():
            return redirect(url_for('doorbells'))

        return redirect(url_for('login'))

    def __endpoint_login(self):
        if self.__authenticate():
            return redirect(url_for('doorbells'))

        if request.method == 'GET':
            return render_template('login.html')

        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('Username and/or password are required.', 'danger')
            return render_template('login.html')

        data = self.__try_login_user(username, password)
        if not data:
            flash('Invalid username or password.', 'danger')
            return render_template('login.html')

        return redirect_after_auth(data[0], data[1])

    def __endpoint_register(self):
        if self.__authenticate():
            return redirect(url_for('doorbells'))

        if request.method == 'GET':
            return render_template('register.html')

        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        if not username or not email or not password:
            flash('Username, email and/or password are required.', 'danger')
            return render_template('register.html')

        password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        data = self.__try_register_user(username, email, password)
        if not data:
            flash('Username or email already taken.', 'danger')
            return render_template('register.html')

        return redirect_after_auth(data[0], data[1])

    def __endpoint_doorbells(self):
        bells = self.__get_doorbells()
        if bells is None:
            return redirect(url_for('index'))

        return render_template('doorbells.html', doorbells=bells)

    def __endpoint_all_streams(self):
        bells = self.__get_doorbells()
        if bells is None:
            return redirect(url_for('index'))

        return render_template('all_streams.html', doorbells=bells)

    def __endpoint_esp_stream(self, uuid: int):
        user_id = self.__authenticate()
        if not user_id or not self.__check_owner(user_id, uuid):
            return b'Content-Length: 0'

        stream_context = stream_with_context(self.__generate_stream(uuid))
        return self.response_class(stream_context, mimetype='multipart/x-mixed-replace; boundary=frame')

    def __endpoint_open_doorbell(self, uuid: int):
        user_id = self.__authenticate()
        if not user_id or not self.__check_owner(user_id, uuid):
            return abort(401)

        if self.__events.on_open_doorbell_requested(uuid):
            return 'OK', 200

        return 'ERROR', 400
