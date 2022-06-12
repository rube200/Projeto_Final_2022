import logging as log
import re
from base64 import b64encode
from collections import namedtuple
from datetime import datetime
from os import environ, path
from sqlite3 import Row
from time import monotonic, sleep

import bcrypt
import jwt
from email_validator import EmailNotValidError, validate_email
from flask import Flask, redirect, url_for, current_app, session, render_template, request, flash, \
    stream_with_context, jsonify
from flask_mail import Mail, Message

from common.alert_type import AlertType, get_alert_message
from common.database_accessor import DatabaseAccessor
from common.esp_client import EspClient
from common.esp_clients import EspClients
from common.esp_events import EspEvents

NAV_DICT = [
    {'id': 'doorbells', 'title': 'Manage Doorbells', 'icon': 'bi-book-fill', 'url': 'doorbells'},
    {'id': 'streams', 'title': 'All Streams', 'icon': 'bi-cast', 'url': 'streams'},
    {'id': 'alerts', 'title': 'Alerts', 'icon': 'bi-bell-fill', 'url': 'alerts'},
    {'id': 'statistics', 'title': 'Statistics', 'icon': 'bi-bar-chart-fill', 'url': 'doorbells'},
]


def convert_image_to_base64(image: bytes) -> str or None:
    if not image:
        return None
    img = b64encode(image).decode('utf-8')
    return f'data:image/jpeg;base64,{img}'


def endpoint_logout():
    session.clear()
    return redirect(url_for('index'))


def redirect_after_auth(username: str, name: str):
    session['token'] = jwt.encode({'username': username}, current_app.config['JWT_SECRET_KEY'], 'HS256')
    session['username'] = username
    session['name'] = name
    return redirect(url_for('doorbells'))


class WebServer(DatabaseAccessor, Flask):
    def __init__(self, clients: EspClients, events: EspEvents):
        DatabaseAccessor.__init__(self, environ.get('DATABASE') or 'esp32cam.sqlite')
        Flask.__init__(self, __name__)

        self.__clients = clients
        self.__events = events
        self.__events.on_alert += self.__on_alert
        self.config.from_pyfile('flask.cfg')

        if self.config.get('RANDOM_SECRET_KEY'):
            import secrets
            self.config['JWT_SECRET_KEY'] = secrets.token_hex(32)
            self.config['SECRET_KEY'] = secrets.token_hex(32)
        self.__mail = Mail(self)
        self.__setup_db()
        self.__setup_web()

    def __del__(self):
        DatabaseAccessor.__del__(self)
        # todo

    def __setup_db(self):
        con = self._get_connection()
        cursor = con.cursor()

        with self.open_resource(self.config['SCHEMA_FILE']) as f:
            cursor.executescript(f.read().decode('utf-8'))
        con.commit()

        cursor.close()
        con.close()

    def __setup_web(self):
        icon_path = path.join(self.static_folder, 'favicon.png')
        self.icon_base64 = convert_image_to_base64(self.open_resource(icon_path).read())
        self.add_url_rule('/', 'index', self.__endpoint_index)
        self.add_url_rule('/login', 'login', self.__endpoint_login, methods=['GET', 'POST'])
        self.add_url_rule('/register', 'register', self.__endpoint_register, methods=['GET', 'POST'])
        self.add_url_rule('/logout', 'logout', endpoint_logout)
        self.add_url_rule('/doorbells', 'doorbells', self.__endpoint_doorbells)
        self.add_url_rule('/doorbells/<int:uuid>', 'doorbell', self.__endpoint_doorbell, methods=['GET', 'POST'])
        self.add_url_rule('/streams', 'streams', self.__endpoint_streams)
        self.add_url_rule('/streams/<int:uuid>', 'stream', self.__endpoint_stream)
        self.add_url_rule('/alerts', 'alerts', self.__endpoint_alerts)
        self.add_url_rule('/alerts-api', 'alerts-api', self.__endpoint_alerts_api)
        self.add_url_rule('/open_doorbell/<int:uuid>', 'open_doorbell', self.__endpoint_open_doorbell, methods=['POST'])
        self.add_url_rule('/take_picture/<int:uuid>', 'take_picture', self.__endpoint_take_picture, methods=['POST'])
        self.add_url_rule('/alerts2', 'alerts2', self.__endpoint_alerts2)
        self.register_error_handler(400, lambda e: redirect(url_for('index')))
        self.register_error_handler(404, lambda e: redirect(url_for('index')))
        self.template_context_processors[None].append(lambda: dict(debug=self.debug, nav=NAV_DICT))

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

        data = self._get_user(username)
        session['username'] = username = data[0]
        session['name'] = data[1]
        return username

    def __get_doorbells(self):
        username = self.__authenticate()
        if not username:
            return None

        data = self._get_doorbells(username)
        if not data:
            return []

        return [self.__get_doorbell(bell_data) for bell_data in data]

    def __get_doorbell(self, bell_data: Row or dict) -> type:
        doorbell = namedtuple('Bell', 'id, name, image, online')
        doorbell.id = bell_data['id']
        doorbell.name = bell_data['name']

        esp = self.__clients.get_client(doorbell.id)
        if esp:
            camera = esp.camera
            doorbell.image = convert_image_to_base64(camera) or url_for('static', filename='default_profile.png')
            doorbell.online = True
            doorbell.state = 'Online'
        else:
            doorbell.image = url_for('static', filename='default_profile.png')
            doorbell.online = False
            doorbell.state = 'Offline'

        return doorbell

    def __get_alert(self, data: Row, load_images: bool = False):
        filepath = data['path']
        if not path.exists(filepath):
            return None

        doorbell_file = namedtuple('DoorbellFiles', 'id, name, time, image')
        doorbell_file.id = data['id']
        doorbell_file.type = data['type']
        doorbell_file.time = data['time']

        if 'name' in data:
            doorbell_file.name = data['name']
        else:
            doorbell_file.name = 'Bell pressed' if doorbell_file.type is AlertType.Bell else 'Motion detected'

        if load_images:
            with self.open_resource(filepath) as f:
                doorbell_file.image = f.read()
        else:
            doorbell_file.image = data['path']

        if 'checked' in data:
            doorbell_file.checked = data['checked']
        print('1')
        print(type(doorbell_file))
        return doorbell_file

    def __get_alerts(self, exclude_checked: bool = True, load_images: bool = False):
        username = self.__authenticate()
        if not username:
            return None

        data = self._get_alerts(username, exclude_checked)
        if not data:
            return []

        alerts = []
        for alert_data in data:
            alert = self.__get_alert(alert_data, load_images)
            if alert:
                alerts.append(alert)
        return alerts

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

                camera = esp.camera
                if not camera:
                    yield b'--frame\r\nContent-Length: 0'
                    continue

                yield b'--frame\r\nContent-Length: ' + bytes(len(camera)) + \
                      b'\r\nContent-Type: image/jpeg\r\nTransfer-Encoding: chunked\r\n\r\n' + camera + b'\r\n'
        finally:
            self.__events.on_stop_stream_requested(uuid)
            return b'Content-Length: 0'

    def __on_alert(self, client: EspClient, alert_type: AlertType, data: bytes, _) -> None:
        try:
            if alert_type is AlertType.UserPicture or alert_type is AlertType.Invalid:
                return

            doorbell_name = self._get_doorbell_name(client.uuid)
            emails = self._get_alert_emails(client.uuid)
            if not doorbell_name or not emails:
                return

            message = f'{get_alert_message(alert_type)} at {datetime.now()}'
            with self.app_context():
                self.__mail.send(Message(
                    subject=get_alert_message(alert_type),
                    bcc=emails,
                    html=render_template('email.html',
                                         icon=self.icon_base64,
                                         image=convert_image_to_base64(data),
                                         message=message)
                ))
        except Exception as ex:
            log.error(f'Exception while getting email for uuid {client.uuid}: {ex!r}')

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

        data = self._try_login(username, password)
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
        data = self._try_register(username, email, password)
        if not data:
            flash('Username or email already taken.', 'danger')
            return render_template('register.html')

        return redirect_after_auth(data[0], data[1])

    def __endpoint_doorbells(self):
        bells = self.__get_doorbells()
        if bells is None:
            return redirect(url_for('index'))

        return render_template('doorbells.html', doorbells=bells)

    def __endpoint_doorbell(self, uuid: int):
        if request.method == 'POST':
            return self.__doorbell_update(uuid)

        username = self.__authenticate()
        if not username:
            return redirect(url_for('index'))

        if not self._check_owner(username, uuid):
            return redirect(url_for('doorbells'))

        doorbell_data = self._get_doorbell(uuid)
        doorbell = self.__get_doorbell({'id': uuid, 'name': doorbell_data[0]})
        doorbell.emails = doorbell_data[1]

        alerts = self._get_doorbell_alerts(uuid)
        if not alerts:
            return render_template('doorbell.html', doorbell=doorbell)

        doorbell_files = []
        for alert in alerts:
            data = self.__get_alert(alert, True)
            if data:
                doorbell_files.append(data)

        return render_template('doorbell.html', doorbell=doorbell, doorbell_files=doorbell_files)

    def __endpoint_streams(self):
        bells = self.__get_doorbells()
        if bells is None:
            return redirect(url_for('index'))

        return render_template('streams.html', doorbells=bells)

    def __endpoint_stream(self, uuid: int):
        username = self.__authenticate()
        if not username or not self._check_owner(username, uuid):
            return b'Content-Length: 0'

        stream_context = stream_with_context(self.__generate_stream(uuid))
        return self.response_class(stream_context, mimetype='multipart/x-mixed-replace; boundary=frame')

    # todo recheck this one
    def __endpoint_alerts(self):
        username = self.__authenticate()
        if not username:
            return redirect(url_for('index'))

        con = self._get_connection()
        cursor = con.cursor()
        try:
            cursor.execute(
                'SELECT d.id, d.name, n.time, n.path '
                'FROM doorbell d '
                'INNER JOIN alerts n '
                'ON d.id = n.uuid '
                'WHERE d.owner LIKE ? '
                'AND n.type <> 0 '
                'ORDER BY N.time DESC',
                [username])
            rows = cursor.fetchall()
            # types = []
            paths = []
            names = []
            dates = []
            for row in rows:
                # types.append(bell[0])
                paths.append(row[1])
                dates.append(row[2].split(".")[0])  # split to remove milliseconds
                names.append(row[3])

            # return render_template('imageGal.html', types = types, paths = paths, dates = dates, doorbells = names)
            return render_template('notifications.html', paths=paths, dates=dates, doorbells=names)  # todo rename
        finally:
            cursor.close()
            con.close()

    def __endpoint_alerts_api(self):
        alerts = self.__get_alerts(load_images=False)
        if alerts is None:
            return jsonify({'error': 'Not authenticated'}, 401)

        return jsonify(alerts)

    def __endpoint_open_doorbell(self, uuid: int):
        username = self.__authenticate()
        if not username or not self._check_owner(username, uuid):
            return self.response_class('Unauthorized request', 401)

        if self.__events.on_open_doorbell_requested(uuid):
            return self.response_class('Doorbell opened')

        return self.response_class('Doorbell is offline', 404)

    def __endpoint_take_picture(self, uuid: int):
        username = self.__authenticate()
        if not username or not self._check_owner(username, uuid):
            return self.response_class('Unauthorized request', 401)

        esp = self.__clients.get_client(uuid)
        if not esp:
            return self.response_class('Doorbell is offline', 404)

        image, filename = esp.save_picture()
        if not image:
            return self.response_class('Doorbell is offline', 404)

        self._add_alert(uuid, image, filename)
        print(image)  # todo remove
        img = convert_image_to_base64(image)
        print(img)
        return self.response_class(img, mimetype='image/jpeg')

    def __doorbell_update(self, uuid: int):
        username = self.__authenticate()
        if not username or not self._check_owner(username, uuid):
            return self.response_class('Unauthorized request', 401)

        password = request.form.get('password')
        doorbell_name = request.form.get('doorbell-name')
        emails = request.form.get('alert-emails')
        re_emails = re.split('[,;\r\n ]', emails)
        alert_emails = []
        for email in re_emails:
            email.strip()
            if not email:
                continue

            email = email.strip()
            try:
                validate_email(email)
            except EmailNotValidError:
                continue

            alert_emails.append(email.lower())
        if not self._doorbell_update(username, password, uuid, doorbell_name, alert_emails):
            return self.response_class('Unauthorized request', 401)

        return self.response_class('Doorbell updated')

    # todo recheck this one
    def __endpoint_alerts2(self):
        username = self.__authenticate()
        if not username:
            return redirect(url_for('index'))

        con = self._get_connection()
        cursor = con.cursor()
        try:
            cursor.execute(
                'SELECT d.id, d.name, n.time, n.path, n.checked, n.type  '
                'FROM doorbell d '
                'INNER JOIN alerts n '
                'ON d.id = n.uuid '
                'WHERE d.owner LIKE ? '
                'ORDER BY N.time DESC',
                [username])
            rows = cursor.fetchall()
            # types = []
            paths = []
            names = []
            dates = []
            checked = []
            types = []
            for row in rows:
                # types.append(bell[0])
                paths.append(row[3])
                dates.append(row[2].split(".")[0])  # split to remove milliseconds
                names.append(row[1])
                checked.append(row[4])
                types.append(row[5])

            # dummy data
            paths.append(url_for('static', filename='default_profile.png'))
            dates.append('12.2.20')  # split to remove milliseconds
            names.append('doorbell1')
            checked.append(False)
            types.append(0)
            paths.append(url_for('static', filename='default_profile.png'))
            dates.append('12.2.21')  # split to remove milliseconds
            names.append('doorbell2')
            checked.append(False)
            types.append(2)
            paths.append(url_for('static', filename='default_profile.png'))
            dates.append('12.2.23')  # split to remove milliseconds
            names.append('doorbell3')
            checked.append(False)
            types.append(1)
            paths.append(url_for('static', filename='default_profile.png'))
            dates.append('12.2.23')  # split to remove milliseconds
            names.append('doorbell3')
            checked.append(False)
            types.append(1)
            paths.append(url_for('static', filename='default_profile.png'))
            dates.append('12.2.20')  # split to remove milliseconds
            names.append('doorbell1')
            checked.append(True)
            types.append(0)
            paths.append(url_for('static', filename='default_profile.png'))
            dates.append('12.2.21')  # split to remove milliseconds
            names.append('doorbell2')
            checked.append(True)
            types.append(2)
            paths.append(url_for('static', filename='default_profile.png'))
            dates.append('12.2.23')  # split to remove milliseconds
            names.append('doorbell3')
            checked.append(True)
            types.append(1)
            paths.append(url_for('static', filename='default_profile.png'))
            dates.append('12.2.23')  # split to remove milliseconds
            names.append('doorbell3')
            checked.append(True)
            types.append(1)
            paths.append(url_for('static', filename='default_profile.png'))
            dates.append('12.2.20')  # split to remove milliseconds
            names.append('doorbell1')
            checked.append(True)
            types.append(0)
            paths.append(url_for('static', filename='default_profile.png'))
            dates.append('12.2.21')  # split to remove milliseconds
            names.append('doorbell2')
            checked.append(True)
            types.append(2)
            paths.append(url_for('static', filename='default_profile.png'))
            dates.append('12.2.23')  # split to remove milliseconds
            names.append('doorbell3')
            checked.append(True)
            types.append(1)
            paths.append(url_for('static', filename='default_profile.png'))
            dates.append('12.2.23')  # split to remove milliseconds
            names.append('doorbell3')
            checked.append(True)
            types.append(1)
            # return render_template('imageGal.html', types = types, paths = paths, dates = dates, doorbells = names)
            return render_template('alerts.html', paths=paths, dates=dates, doorbells=names, checks=checked,
                                   types=types)
        finally:
            cursor.close()
            con.close()
