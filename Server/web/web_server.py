import logging as log
import re
from base64 import b64encode
from collections import namedtuple
from datetime import datetime
from mimetypes import guess_type
from os import environ, path, makedirs
from sqlite3 import Row
from time import monotonic, sleep, time

import bcrypt
import jwt
from email_validator import EmailNotValidError, validate_email
from flask import Flask, redirect, url_for, current_app, session, render_template, request, flash, \
    stream_with_context, jsonify, send_from_directory
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename

from common.alert_type import AlertType, get_alert_message
from common.database_accessor import DatabaseAccessor
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


valid_files = ('jpg', 'jpeg', 'png', 'mp4')


def is_valid_file(filename: str, filepath: str) -> bool:
    if not filename.endswith(valid_files):
        return False

    return path.exists(filepath)


class WebServer(DatabaseAccessor, Flask):
    def __init__(self, clients: EspClients, events: EspEvents):
        DatabaseAccessor.__init__(self, environ.get('DATABASE') or 'esp32cam.sqlite')
        Flask.__init__(self, __name__)

        self.__clients = clients
        self.__events = events
        self.__events.on_alert += self.__on_alert
        self.config.from_pyfile('flask.cfg')

        environ['ESP_FILES_DIR'] = self.__esp_full_path = path.join(self.root_path, self.config['ESP_FILES_DIR'])
        if not path.exists(self.__esp_full_path):
            makedirs(self.__esp_full_path)

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
        self.add_url_rule('/alerts', 'alerts', self.__endpoint_alerts)
        self.add_url_rule('/alerts-count', 'alerts-count', self.__endpoint_alerts_count)
        self.add_url_rule('/doorbells', 'doorbells', self.__endpoint_doorbells)
        self.add_url_rule('/doorbells/<int:uuid>', 'doorbell', self.__endpoint_doorbell, methods=['GET', 'POST'])
        self.add_url_rule('/streams', 'streams', self.__endpoint_streams)
        self.add_url_rule('/streams/<int:uuid>', 'stream', self.__endpoint_stream)
        self.add_url_rule('/get-resource/<string:filename>', 'get-resource', self.__endpoint_get_resource)
        self.add_url_rule('/open_doorbell/<int:uuid>', 'open_doorbell', self.__endpoint_open_doorbell, methods=['POST'])
        self.add_url_rule('/take_picture/<int:uuid>', 'take_picture', self.__endpoint_take_picture, methods=['POST'])
        self.add_url_rule('/alerts2', 'alerts2', self.__endpoint_alerts2, methods=['GET', 'POST'])
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

    def __convert_alert(self, alert_data: Row or dict, need_file: bool = False):
        col = alert_data.keys()
        alert = namedtuple('DoorbellAlert', 'id, type, time')
        alert.id = alert_data['id']
        alert.type = AlertType(alert_data['type'])
        alert.time = alert_data['time']
        alert.filename = alert_data['filename'] if 'filename' in col else None
        if alert.filename and path.exists(path.join(self.__esp_full_path, alert.filename)):
            alert.mimetype = guess_type(alert.filename)[0]
        else:
            if need_file:
                return None

            alert.mimetype = 'image/jpeg'

        alert.uuid = alert_data['uuid'] if 'uuid' in col else None
        alert.name = alert_data['name'] if 'name' in col else None
        alert.checked = alert_data['checked'] if 'checked' in col else None
        alert.notes = alert_data['notes'] if 'notes' in col else None
        return alert

    def __convert_doorbell(self, bell_data: Row or dict):
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

    def __get_doorbells(self):
        username = self.__authenticate()
        if not username:
            return None

        data = self._get_doorbells(username)
        if not data:
            return []

        return [self.__convert_doorbell(bell_data) for bell_data in data]

    def __redirect_after_auth(self, username: str, name: str):
        session['token'] = jwt.encode({'username': username}, self.config['JWT_SECRET_KEY'], 'HS256')
        session['username'] = username
        session['name'] = name
        return redirect(url_for('doorbells'))

    def __on_alert(self, uuid: int, alert_type: AlertType, data: dict):
        try:
            if alert_type is AlertType.Invalid or alert_type is AlertType.UserPicture:
                return

            doorbell_name = self._get_doorbell_name(uuid)
            emails = self._get_alert_emails(uuid)
            if not doorbell_name or not emails:
                return

            alert_message = get_alert_message(alert_type)
            alert_time = data.get('time') or time()
            date = datetime.fromtimestamp(alert_time).strftime('%Y-%m-%d %H:%M')

            image = convert_image_to_base64(data['image']) if 'image' in data else None
            if alert_type is AlertType.Bell or alert_type is AlertType.Movement:
                message = f'{alert_message} at your doorbell({doorbell_name})'
            elif alert_type is AlertType.NewBell:
                message = f'{alert_message}({doorbell_name}) to your account'
            else:
                message = f'{alert_message} - {doorbell_name}'

            with self.app_context():
                self.__mail.send(Message(
                    subject=get_alert_message(alert_type),
                    bcc=emails,
                    html=render_template('email.html',
                                         icon=self.icon_base64,
                                         image=image,
                                         message=message,
                                         time=f'Time: {date}')
                ))
        except Exception as ex:
            log.error(f'Exception while getting email for uuid {uuid}: {ex!r}')

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

        return self.__redirect_after_auth(data[0], data[1])

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

        return self.__redirect_after_auth(data[0], data[1])

    def __endpoint_doorbells(self):
        bells = self.__get_doorbells()
        if bells is None:
            return redirect(url_for('index'))

        return render_template('doorbells.html', doorbells=bells)

    def __endpoint_doorbell(self, uuid: int):
        if request.method == 'POST':
            return self.__update_doorbell(uuid)

        username = self.__authenticate()
        if not username:
            return redirect(url_for('index'))

        if not self._check_owner(username, uuid):
            return redirect(url_for('doorbells'))

        doorbell_data = self._get_doorbell(uuid)
        doorbell = self.__convert_doorbell({'id': uuid, 'name': doorbell_data[0]})
        doorbell.emails = doorbell_data[1]

        alerts = self._get_doorbell_alerts(uuid, [AlertType.Bell, AlertType.Movement, AlertType.UserPicture], False)
        if not alerts:
            return render_template('doorbell.html', doorbell=doorbell)

        doorbell_files = []
        for alert in alerts:
            data = self.__convert_alert(alert, True)
            if not data:
                continue

            if not data.name:
                data.name = get_alert_message(data.type)
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

    def __endpoint_alerts_count(self):
        username = self.__authenticate()
        if not username:
            return {'error': 'Unauthorized request'}, 401

        alerts_count = self._get_alerts_count(username)
        return jsonify(alerts_count), 200

    def __endpoint_open_doorbell(self, uuid: int):
        username = self.__authenticate()
        if not username or not self._check_owner(username, uuid):
            return {'error': 'Unauthorized request'}, 401

        if not self.__events.on_open_doorbell_requested(uuid):
            return {'error': 'Doorbell is offline'}, 404

        return jsonify('Doorbell opened'), 200

    def __endpoint_take_picture(self, uuid: int):
        username = self.__authenticate()
        if not username or not self._check_owner(username, uuid):
            return {'error': 'Unauthorized request'}, 401

        esp = self.__clients.get_client(uuid)
        if not esp:
            return {'error': 'Doorbell is offline'}, 404

        image, filename = esp.save_picture()
        if not image:
            return {'error': 'Doorbell is offline'}, 404

        self.__events.on_alert(uuid, AlertType.UserPicture, {'filename': filename, 'image': image})
        return {'filename': filename, 'mimetype': 'image/jpeg'}, 200

    def __update_doorbell(self, uuid: int):
        doorbell_name = request.form.get('doorbell-name')
        emails = request.form.get('alert-emails')
        password = request.form.get('password')
        if not doorbell_name or not emails or not password:
            return {'error': 'Missing parameters'}, 400

        username = self.__authenticate()
        if not username or not self._check_owner(username, uuid):
            return {'error': 'Unauthorized request'}, 401

        re_emails = re.split('[,;\r\n ]', emails)
        alert_emails = []
        for email in re_emails:
            email = email.strip().lower()
            if not email:
                continue

            try:
                validate_email(email)
            except EmailNotValidError:
                continue

            if email not in alert_emails:
                alert_emails.append(email)

        if not self._doorbell_update(username, password, uuid, doorbell_name, alert_emails):
            return {'error': 'Unauthorized request'}, 401

        return {
                   'id': uuid,
                   'name': doorbell_name,
                   'emails': alert_emails
               }, 200

    def __endpoint_get_resource(self, filename: str):
        filename = secure_filename(filename.lower())
        filepath = path.join(self.__esp_full_path, filename)
        if not is_valid_file(filename, filepath):
            return send_from_directory(self.static_folder, 'default_profile.png'), 404

        username = self.__authenticate()
        if not username or not self._check_owner_file(username, filename):
            return self.response_class('Unauthorized request', 401)

        return send_from_directory(self.config['ESP_FILES_DIR'], filename)

    # todo recheck this one
    def __endpoint_alerts(self):
        username = self.__authenticate()
        if not username:
            return redirect(url_for('index'))

        con = self._get_connection()
        cursor = con.cursor()
        try:
            cursor.execute(
                'SELECT d.id, d.name, n.time, n.filename '
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

    # todo recheck this one
    def __endpoint_alerts2(self):
        username = self.__authenticate()
        if not username:
            return redirect(url_for('index'))
        if request.method == 'POST':
            data = request.form.get('date')
            # mark all alerts dated older than or equal to date as read
            con = self._get_connection()
            cursor = con.cursor()
            try:
                cursor.execute(
                    'UPDATE alerts  '
                    'SET checked = True '
                    'WHERE time <= ? '
                    [data])
                con.commit()
                return render_template('alerts.html')
            finally:
                cursor.close()
                con.close()

        # con = self._get_connection()
        # cursor = con.cursor()
        paths = []
        names = []
        dates = []
        checked = []
        types = []
        notes = []
        """try:
            
            cursor.execute(
                'SELECT d.id, d.name, n.time, n.filename, n.checked, n.type, n.notes  '
                'FROM doorbell d '
                'INNER JOIN alerts n '
                'ON d.id = n.uuid '
                'WHERE d.owner LIKE ? '
                'ORDER BY N.time DESC',
                [username])
            rows = cursor.fetchall()
            
            for row in rows:
                # types.append(bell[0])
                paths.append(row[3])
                dates.append(row[2].split(".")[0])  # split to remove milliseconds
                names.append(row[1])
                checked.append(row[4])
                types.append(row[5])
                notes.append(row[6])
            """
        # dummy data
        paths.append(url_for('static', filename='ronaldo.mp4'))
        dates.append('12.2.20')  # split to remove milliseconds
        names.append('doorbell1')
        checked.append(False)
        types.append(4)
        notes.append("ligma")
        paths.append(url_for('static', filename='ronaldo.mp4'))
        dates.append('12.2.20')  # split to remove milliseconds
        names.append('doorbell1')
        checked.append(False)
        types.append(3)
        notes.append("ligma")
        paths.append(url_for('static', filename='default_profile.png'))
        dates.append('12.2.20')  # split to remove milliseconds
        names.append('doorbell1')
        checked.append(False)
        types.append(2)
        notes.append("ligma")
        paths.append(url_for('static', filename='default_profile.png'))
        dates.append('12.2.20')  # split to remove milliseconds
        names.append('doorbell1')
        checked.append(False)
        types.append(3)
        notes.append("ligma")
        paths.append(url_for('static', filename='default_profile.png'))
        dates.append('12.2.20')  # split to remove milliseconds
        names.append('doorbell1')
        checked.append(False)
        types.append(1)
        notes.append("ligma")
        paths.append(url_for('static', filename='default_profile.png'))
        dates.append('12.2.20')  # split to remove milliseconds
        names.append('doorbell1')
        checked.append(False)
        types.append(2)
        notes.append("ligma")

        # return render_template('imageGal.html', types = types, paths = paths, dates = dates, doorbells = names)
        return render_template('alerts.html', paths=paths, dates=dates, doorbells=names, checks=checked,
                               types=types, notes=notes)
        # finally:
        #    cursor.close()
        #    con.close()
