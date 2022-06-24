import logging as log
import re
from base64 import b64encode
from datetime import datetime
from mimetypes import guess_type
from os import environ, path, makedirs
from sqlite3 import Row
from time import monotonic, sleep, time
from traceback import format_exc
from typing import Callable, Tuple

import bcrypt
import jwt
from email_validator import EmailNotValidError, validate_email
from flask import Flask, redirect, url_for, current_app, session, render_template, request, flash, \
    stream_with_context, send_from_directory, has_request_context
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename

from common.alert_type import AlertType, get_alert_type_message
from common.database_accessor import DatabaseAccessor
from common.esp_client import EspClient
from common.esp_clients import EspClients
from common.esp_events import EspEvents

NAV_DICT = [
    {'id': 'doorbells', 'title': 'Manage Doorbells', 'icon': 'bi-book-fill', 'url': 'doorbells'},
    {'id': 'streams', 'title': 'All Streams', 'icon': 'bi-cast', 'url': 'streams'},
    {'id': 'captures', 'title': 'Captures', 'icon': 'bi-camera-video-fill', 'url': 'captures'},
    {'id': 'alerts', 'title': 'Alerts', 'icon': 'bi-bell-fill', 'url': 'alerts'}
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
        self.add_url_rule('/login', 'login', self.__endpoint_login, defaults={'page_to_redirect': None},
                          methods=['GET', 'POST'])
        self.add_url_rule('/login/<string:page_to_redirect>', 'login', self.__endpoint_login, methods=['GET', 'POST'])
        self.add_url_rule('/register', 'register', self.__endpoint_register, methods=['GET', 'POST'])
        self.add_url_rule('/register/<string:page_to_redirect>', 'register', self.__endpoint_register,
                          defaults={'page_to_redirect': None}, methods=['GET', 'POST'])
        self.add_url_rule('/logout', 'logout', endpoint_logout)
        self.add_url_rule('/alerts', 'alerts', self.__endpoint_alerts, methods=['GET', 'POST'])
        self.add_url_rule('/captures', 'captures', self.__endpoint_captures)
        self.add_url_rule('/doorbells', 'doorbells', self.__endpoint_doorbells)
        self.add_url_rule('/doorbells/<int:uuid>', 'doorbell', self.__endpoint_doorbell, methods=['GET', 'POST'])
        self.add_url_rule('/streams', 'streams', self.__endpoint_streams)
        self.add_url_rule('/streams/<int:uuid>', 'stream', self.__endpoint_stream)
        self.add_url_rule('/get-doorbells-info', 'get-doorbells-info', self.__endpoint_get_doorbells_info)
        self.add_url_rule('/get-new-alerts/<int:current_alert_id>', 'get-new-alerts', self.__endpoint_get_new_alerts)
        self.add_url_rule('/get-new-captures/<int:current_capture_id>', 'get-new-captures',
                          self.__endpoint_get_new_captures)
        self.add_url_rule('/get-resource/<string:filename>', 'get-resource', self.__endpoint_get_resource)
        self.add_url_rule('/open_doorbell/<int:uuid>', 'open_doorbell', self.__endpoint_open_doorbell, methods=['POST'])
        self.add_url_rule('/take_picture/<int:uuid>', 'take_picture', self.__endpoint_take_picture, methods=['POST'])
        self.register_error_handler(400, lambda e: redirect(url_for('index')))
        self.register_error_handler(404, lambda e: redirect(url_for('index')))
        self.template_context_processors[None].append(self.__inject_content)

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
        if need_file:
            if 'filename' not in col:
                return None

            filename = alert_data['filename']
            if not filename or not path.exists(path.join(self.__esp_full_path, filename)):
                return None

            mimetype = guess_type(filename)[0]
        else:
            filename = alert_data['filename'] if 'filename' in col else None
            mimetype = 'image/jpeg'

        return {
            'id': alert_data['id'],
            'type': alert_data['type'],
            'time': alert_data['time'],
            'filename': filename,
            'mimetype': mimetype,
            'uuid': alert_data['uuid'] if 'uuid' in col else None,
            'name': alert_data['name'] if 'name' in col else None,
            'checked': alert_data['checked'] if 'checked' in col else None,
            'notes': alert_data['notes'] if 'notes' in col else None
        }

    def __convert_captures(self, captures_data: Row or dict):
        doorbell_files = []
        for capture in captures_data:
            data = self.__convert_alert(capture, True)
            if not data:
                continue

            message = data.get('message')
            if not message:
                data['message'] = get_alert_type_message(data['type'])
            doorbell_files.append(data)

        return doorbell_files

    def __convert_doorbell(self, bell_data: Row or dict, get_camera: bool):
        uuid = bell_data['id']
        doorbell = {
            'uuid': uuid,
            'name': bell_data['name'],
        }

        default_image = url_for('static', filename='default_profile.png')
        esp = self.__clients.get_client(uuid)
        if esp:
            if get_camera:
                doorbell['image'] = convert_image_to_base64(esp.camera) or default_image
            else:
                doorbell['image'] = default_image
            doorbell['online'] = True
            doorbell['state'] = 'Online'
        else:
            doorbell['image'] = default_image
            doorbell['online'] = False
            doorbell['state'] = 'Offline'

        return doorbell

    def __generate_stream(self, uuid: int):
        esp = self.__clients.get_client(uuid)
        if not esp:
            return b'Content-Length: 0'

        start_at = monotonic() + 10
        esp.start_stream(False)
        try:
            while True:
                sleep(.05)
                if not esp or not esp.uuid:
                    esp = self.__clients.get_client(uuid)
                    continue

                # noinspection PyUnboundLocalVariable
                if start_at <= monotonic():
                    start_at = monotonic() + 10
                    esp.start_stream(True)

                camera = esp.camera
                if not camera:
                    yield b'--frame\r\nContent-Length: 0'
                    continue

                yield b'--frame\r\nContent-Length: ' + bytes(len(camera)) + \
                      b'\r\nContent-Type: image/jpeg\r\nTransfer-Encoding: chunked\r\n\r\n' + camera + b'\r\n'
        finally:
            esp.stop_stream()
            return b'Content-Length: 0'

    def __get_new_alerts(self, username: str):
        pass

    def __get_doorbells(self, need_camera: bool):
        username = self.__authenticate()
        if not username:
            return None

        data = self._get_doorbells(username)
        if not data:
            return []

        return [self.__convert_doorbell(bell_data, need_camera) for bell_data in data]

    def __inject_content(self):
        data = {
            'debug': self.debug,
            'nav': NAV_DICT
        }

        if not has_request_context():
            return data

        return data

    def __redirect_after_auth(self, username: str, name: str, page_to_redirect: str):
        session['token'] = jwt.encode({'username': username}, self.config['JWT_SECRET_KEY'], 'HS256')
        session['username'] = username
        session['name'] = name
        return redirect(url_for(page_to_redirect if page_to_redirect else 'doorbells'))

    def __on_alert(self, uuid: int, alert_type: AlertType, data: dict):
        try:
            if alert_type is AlertType.Invalid or alert_type is AlertType.UserPicture:
                return

            doorbell_name = self._get_doorbell_name(uuid)
            emails = self._get_alert_emails(uuid)
            if not doorbell_name or not emails:
                return

            alert_message = get_alert_type_message(alert_type)
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
                    subject=get_alert_type_message(alert_type),
                    bcc=emails,
                    html=render_template('email.html',
                                         icon=self.icon_base64,
                                         image=image,
                                         message=message,
                                         url_for_alerts=url_for('alerts'),
                                         time=f'Time: {date}')
                ))
        except Exception as ex:
            log.error(f'Exception while getting email for uuid {uuid}: {ex!r}')
            log.error(format_exc())

    def __endpoint_index(self):
        return redirect(url_for('doorbells' if self.__authenticate() else 'login'))

    def __endpoint_login(self, page_to_redirect: str):
        if self.__authenticate():
            return redirect(url_for(page_to_redirect if page_to_redirect else 'doorbells'))

        if request.method == 'GET':
            return render_template('login.html', page_to_redirect=page_to_redirect)

        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('Username and/or password are required.', 'danger')
            return render_template('login.html', page_to_redirect=page_to_redirect)

        data = self._try_login(username, password)
        if not data:
            flash('Invalid username or password.', 'danger')
            return render_template('login.html', page_to_redirect=page_to_redirect)

        return self.__redirect_after_auth(data[0], data[1], page_to_redirect)

    def __endpoint_register(self, page_to_redirect: str):
        if self.__authenticate():
            return redirect(url_for(page_to_redirect if page_to_redirect else 'doorbells'))

        if request.method == 'GET':
            return render_template('register.html', page_to_redirect=page_to_redirect)

        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        if not username or not email or not password:
            flash('Username, email and/or password are required.', 'danger')
            return render_template('register.html', page_to_redirect=page_to_redirect)

        password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        data = self._try_register(username, email, password)
        if not data:
            flash('Username or email already taken.', 'danger')
            return render_template('register.html', page_to_redirect=page_to_redirect)

        return self.__redirect_after_auth(data[0], data[1], page_to_redirect)

    def __endpoint_captures(self):
        username = self.__authenticate()
        if not username:
            return redirect(url_for('login', page_to_redirect='captures'))

        captures_data = self._get_user_captures(username)
        if not captures_data:
            return render_template('captures.html')

        captures = self.__convert_captures(captures_data)
        return render_template('captures.html', doorbell_files=captures)

    def __endpoint_doorbells(self):
        bells = self.__get_doorbells(True)
        if bells is None:
            return redirect(url_for('login', page_to_redirect='doorbells'))

        return render_template('doorbells.html', doorbells=bells)

    # todo adding support to relay
    def __endpoint_doorbell(self, uuid: int):
        if request.method == 'POST':
            return self.__update_doorbell(uuid)

        username = self.__authenticate()
        if not username:
            return redirect(url_for('login', page_to_redirect='doorbells'))

        if not self._check_owner(username, uuid):
            return redirect(url_for('doorbells'))

        doorbell_data = self._get_doorbell(uuid)
        doorbell = self.__convert_doorbell({'id': uuid, 'name': doorbell_data[0]}, True)
        doorbell.emails = doorbell_data[1]
        return render_template('doorbell.html', doorbell=doorbell)

    def __endpoint_streams(self):
        bells = self.__get_doorbells(True)
        if bells is None:
            return redirect(url_for('login', page_to_redirect='streams'))

        return render_template('streams.html', doorbells=bells)

    def __endpoint_stream(self, uuid: int):
        username = self.__authenticate()
        if not username or not self._check_owner(username, uuid):
            return b'Content-Length: 0'

        stream_context = stream_with_context(self.__generate_stream(uuid))
        return self.response_class(stream_context, mimetype='multipart/x-mixed-replace; boundary=frame')

    def __endpoint_get_doorbells_info(self):
        doorbells = self.__get_doorbells(False)
        if doorbells is None:
            return {'error': 'Unauthorized request'}, 401

        return {'doorbells': doorbells}, 200

    def __endpoint_get_new_alerts(self, current_alert_id: int):
        username = self.__authenticate()
        if not username:
            return {'error': 'Unauthorized request'}, 401

        alerts_data = self._get_user_alerts_after(username, current_alert_id)
        if not alerts_data:
            return {'alerts': [], 'lastAlertId': 0}, 200

        alerts = self.__convert_captures(alerts_data)
        if not alerts:
            return {'alerts': [], 'lastAlertId': 0}, 200

        return {'alerts': alerts, 'lastAlertId': alerts[0]['id']}, 200

    def __endpoint_get_new_captures(self, current_capture_id: int):
        username = self.__authenticate()
        if not username:
            return {'error': 'Unauthorized request'}, 401

        captures_data = self._get_user_captures_after(username, current_capture_id)
        if not captures_data:
            return {}, 200

        captures = self.__convert_captures(captures_data)
        if not captures:
            return {}, 200

        return {'captures': captures, 'lastCaptureId': captures[0]['id']}, 200

    def __endpoint_get_resource(self, filename: str):
        filename = secure_filename(filename.lower())
        filepath = path.join(self.__esp_full_path, filename)
        if not is_valid_file(filename, filepath):
            return send_from_directory(self.static_folder, 'default_profile.png'), 404

        username = self.__authenticate()
        if not username or not self._check_owner_file(username, filename):
            return self.response_class('Unauthorized request', 401)

        return send_from_directory(self.config['ESP_FILES_DIR'], filename)

    def __open_door_take_picture(self, uuid: int, alert_type: AlertType,
                                 esp_func: Callable[[EspClient], Tuple[bytes or None, str]]):
        username = self.__authenticate()
        if not username or not self._check_owner(username, uuid):
            return {'error': 'Unauthorized request'}, 401

        esp = self.__clients.get_client(uuid)
        if not esp:
            return {'error': 'Doorbell is offline'}, 404

        image, filename = esp_func(esp)
        if not image:
            return {'error': 'Doorbell is offline'}, 404

        self.__events.on_alert(uuid, alert_type, {'filename': filename, 'image': image, 'checked': True})
        return {'filename': filename, 'mimetype': 'image/jpeg'}, 200

    def __endpoint_open_doorbell(self, uuid: int):
        return self.__open_door_take_picture(uuid, AlertType.UserPicture, lambda esp: esp.open_doorbell)

    def __endpoint_take_picture(self, uuid: int):
        return self.__open_door_take_picture(uuid, AlertType.UserPicture, lambda esp: esp.save_picture)

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

    # todo recheck this one
    def __endpoint_alerts(self):
        username = self.__authenticate()
        if not username:
            return redirect(url_for('login', page_to_redirect='alerts'))

        if request.method == 'POST':
            data = request.form.get('date')
            print(data)
            # mark all alerts dated older than or equal to date as read
            con = self._get_connection()
            cursor = con.cursor()
            try:
                cursor.execute('UPDATE alerts SET checked = ? WHERE time <= ? ', (True, data))
                con.commit()
                return render_template('alerts.html')
            finally:
                cursor.close()
                con.close()

        # con = self._get_connection()
        # cursor = con.cursor()
        # cursor.execute("INSERT INTO doorbell VALUES (1, 'doorbell_name', 'joao', '12.2.2020') ")
        # con.commit()
        # cursor.execute("INSERT INTO alerts VALUES ('1', '1', ?, '3', False, ?, 'sup sup') ", (datetime.now(), url_for('static', filename='ronaldo.mp4')))
        # con.commit()
        # cursor.execute("INSERT INTO alerts VALUES ('2', '2', ?, '3', False, ?, 'sup sup') ", (datetime.now(), url_for('static', filename='ronaldo.mp4')))
        # con.commit()
        # cursor.close()
        # con.close()

        try:
            con = self._get_connection()
            cursor = con.cursor()
            paths = []
            names = []
            dates = []
            checked = []
            types = []
            notes = []
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
                dates.append(row[2])  # .split(".")[0])  # split to remove milliseconds
                names.append(row[1])
                checked.append(row[4])
                types.append(row[5])
                notes.append(row[6])

            # dummy data
            """
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
            notes.append("ligma")"""

            # return render_template('imageGal.html', types = types, paths = paths, dates = dates, doorbells = names)
            return render_template('alerts.html', paths=paths, dates=dates, doorbells=names, checks=checked,
                                   types=types, notes=notes)
        finally:
            cursor.close()
            con.close()
