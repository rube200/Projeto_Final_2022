import logging as log
import re
from base64 import b64encode
from collections import namedtuple
from os import environ, path
from time import monotonic, sleep

import bcrypt
import jwt
from email_validator import EmailNotValidError, validate_email
from flask import Flask, redirect, url_for, current_app, abort, session, render_template, request, flash, \
    stream_with_context, jsonify
from flask_mail import Mail

from common.database_accessor import DatabaseAccessor
from common.esp_client import EspClient
from common.esp_clients import EspClients
from common.esp_events import EspEvents
from common.notification_type import NotificationType

NAV_DICT = [
    {'id': 'doorbells', 'title': 'Manage Doorbells', 'icon': 'bi-book-fill', 'url': 'doorbells'},
    {'id': 'streams', 'title': 'All Streams', 'icon': 'bi-cast', 'url': 'streams'},
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
        self.add_url_rule('/', 'index', self.__endpoint_index)
        self.add_url_rule('/login', 'login', self.__endpoint_login, methods=['GET', 'POST'])
        self.add_url_rule('/register', 'register', self.__endpoint_register, methods=['GET', 'POST'])
        self.add_url_rule('/logout', 'logout', endpoint_logout)
        self.add_url_rule('/doorbells', 'doorbells', self.__endpoint_doorbells)
        self.add_url_rule('/doorbells/<int:uuid>', 'doorbell', self.__endpoint_doorbell, methods=['GET', 'POST'])
        self.add_url_rule('/streams', 'streams', self.__endpoint_streams)
        self.add_url_rule('/streams/<int:uuid>', 'stream', self.__endpoint_stream)
        self.add_url_rule('/notifications', 'notifications', self.__endpoint_notifications)
        self.add_url_rule('/notifications-api', 'notifications-api', self.__endpoint_notifications_api)
        self.add_url_rule('/open_doorbell/<int:uuid>', 'open_doorbell', self.__endpoint_open_doorbell)
        self.add_url_rule('/alerts', 'alerts', self.__endpoint_open_alerts)
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

        data = self._get_user_by_username(username)
        session['user_id'] = username = data[0]
        session['user_name'] = data[1]
        return username

    def __get_doorbells(self):
        username = self.__authenticate()
        if not username:
            return None

        data = self._get_doorbells_by_owner(username)
        if not data:
            return []

        bells = []
        for bell_data in data:
            tmp_bell = namedtuple('Bell', 'id, name, image, state, online')
            tmp_bell.id = bell_data['id']
            tmp_bell.name = bell_data['name']

            esp = self.__clients.get_client(tmp_bell.id)
            if esp:
                camera = esp.camera
                if camera:
                    img = b64encode(camera).decode('utf-8')
                    tmp_bell.image = f'data:image/jpeg;base64,{img}'
                else:
                    tmp_bell.image = url_for('static', filename='default_profile.png')
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

                camera = esp.camera
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
            emails = self._get_alert_emails(client.uuid)
            if not emails:
                return
            # todo email set
            # with self.app_context():
            #    self.__mail.send(
            #        Message('Doorbell pressed' if notification_type is NotificationType.Bell else 'Motion detected',
            #                [emails], 'GOT CHECK IT NOW. MOTHERFUCKER'))#email
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

        data = self._try_login_user(username, password)
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
        data = self._try_register_user(username, email, password)
        if not data:
            flash('Username or email already taken.', 'danger')
            return render_template('register.html')

        return redirect_after_auth(data[0], data[1])

    def __endpoint_doorbells(self):
        bells = self.__get_doorbells()
        if bells is None:
            return redirect(url_for('index'))

        return render_template('doorbells.html', doorbells=bells)

    # todo recheck this one
    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def __endpoint_doorbell(self, uuid: int):
        if request.method == 'POST':
            return self.__doorbell_update(uuid)

        username = self.__authenticate()
        if not username:
            return redirect(url_for('index'))

        if not self._check_owner(username, uuid):
            return redirect(url_for('doorbells'))

        data = self._get_doorbell_by_uuid(uuid)
        doorbell = namedtuple('Bell', 'id, name, emails, image, online')
        doorbell.id = uuid
        doorbell.name = data[0]
        doorbell.emails = data[1]

        esp = self.__clients.get_client(uuid)
        if esp:
            camera = esp.camera
            if camera:
                img = b64encode(camera).decode('utf-8')
                doorbell.image = f'data:image/jpeg;base64,{img}'
            else:
                doorbell.image = url_for('static', filename='default_profile.png')
            doorbell.online = True
        else:
            doorbell.image = url_for('static', filename='default_profile.png')
            doorbell.online = False

        con = self._get_connection()
        cursor = con.cursor()
        # get doorbell data
        try:
            cursor.execute(
                'SELECT d.id, d.name, n.time, n.path '
                'FROM doorbell d '
                'INNER JOIN notifications n '
                'ON d.id = n.uuid '
                'WHERE d.owner LIKE ? '
                'AND n.type <> 0 '
                'AND d.id like ?'
                'ORDER BY N.time DESC',
                [username, uuid])
            rows = cursor.fetchall()
            paths = []
            names = []
            dates = []
            for row in rows:
                paths.append(row[1])
                dates.append(row[2])  # split to remove milliseconds
                names.append(row[3])
        finally:
            cursor.close()
            con.close()
        return render_template('doorbell.html', doorbell=doorbell)

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

    def __get_notifications(self, exclude_checked: bool = True):
        username = self.__authenticate()
        if not username:
            return None

        data = self._get_notifications_by_username(username, exclude_checked)
        if not data:
            return []

        notifications = []
        for notification_data in data:
            filepath = notification_data['path']
            if not path.exists(filepath):
                continue

            tmp_notification = {
                'id': notification_data['id'],
                'name': notification_data['name'],
                'time': notification_data['time'],
                'type': notification_data['type'],
                'path': filepath
            }

            if not exclude_checked:
                tmp_notification['checked'] = notification_data['checked']

            notifications.append(tmp_notification)
        return notifications

    # todo recheck this one
    def __endpoint_notifications(self):
        username = self.__authenticate()
        if not username:
            return redirect(url_for('index'))

        con = self._get_connection()
        cursor = con.cursor()
        try:
            cursor.execute(
                'SELECT d.id, d.name, n.time, n.path '
                'FROM doorbell d '
                'INNER JOIN notifications n '
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
            return render_template('notifications.html', paths=paths, dates=dates, doorbells=names)
        finally:
            cursor.close()
            con.close()

    def __endpoint_notifications_api(self):
        notifications = self.__get_notifications()
        if notifications is None:
            return jsonify({'error': 'Not authenticated'}, 401)

        return jsonify(notifications)

    def __endpoint_open_doorbell(self, uuid: int):
        username = self.__authenticate()
        if not username or not self._check_owner(username, uuid):
            return abort(401)

        if self.__events.on_open_doorbell_requested(uuid):
            return 'OK', 200

        return 'ERROR', 400

    def __doorbell_update(self, uuid: int):
        username = self.__authenticate()
        if not username or not self._check_owner(username, uuid):
            return abort(401)

        password = request.form.get('password')
        doorbell_name = request.form.get('doorbell-name')
        emails = request.form.get('alert-emails')
        re_emails = re.split('[,;\r\n ]', emails)
        alert_emails = []
        for email in re_emails:
            if not email:
                continue

            try:
                validate_email(email)
            except EmailNotValidError:
                continue

            alert_emails.append(email.strip())
        self._doorbell_update(username, password, uuid, doorbell_name, alert_emails)
        # todo check return from update
        return 'OK', 200

    def __endpoint_open_alerts(self):
        username = self.__authenticate()
        if not username:
            return redirect(url_for('index'))

        con = self._get_connection()
        cursor = con.cursor()
        try:
            cursor.execute(
                'SELECT d.id, d.name, n.time, n.path, n.checked, n.type  '
                'FROM doorbell d '
                'INNER JOIN notifications n '
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


            #dummy data
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
            checked.append(False)
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
            return render_template('alerts.html', paths=paths, dates=dates, doorbells=names, checks = checked, types = types)
        finally:
            cursor.close()
            con.close()
