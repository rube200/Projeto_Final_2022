import logging as log
import re
from base64 import b64encode
from datetime import datetime
from mimetypes import guess_type
from os import environ, path, makedirs
from sqlite3 import Row
from time import monotonic, sleep, time
from traceback import format_exc
from typing import Union

import bcrypt
import jwt
from email_validator import EmailNotValidError, validate_email
from flask import Flask, redirect, url_for, current_app, session, render_template, request, flash, \
    stream_with_context, send_from_directory, has_request_context
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename

from common.alert_type import AlertType, get_alert_type_message
from common.database_accessor import DatabaseAccessor
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
        makedirs(self.__esp_full_path, 770, True)
        if self.config.get('RANDOM_SECRET_KEY'):
            import secrets
            self.config['JWT_SECRET_KEY'] = secrets.token_hex(32)
            self.config['SECRET_KEY'] = secrets.token_hex(32)

        self.jinja_env.add_extension('jinja2.ext.do')
        self.__mail = Mail(self)
        self.__setup_db()
        self.__setup_web()

    def __del__(self):
        DatabaseAccessor.__del__(self)
        self.__events.on_alert -= self.__on_alert
        # todo finish

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
        self.add_url_rule('/login', 'login', self.__endpoint_login, defaults={'page_to_redirect': ''},
                          methods=['GET', 'POST'])
        self.add_url_rule('/login/<string:page_to_redirect>', 'login', self.__endpoint_login, methods=['GET', 'POST'])
        self.add_url_rule('/register', 'register', self.__endpoint_register, defaults={'page_to_redirect': ''},
                          methods=['GET', 'POST'])
        self.add_url_rule('/register/<string:page_to_redirect>', 'register', self.__endpoint_register,
                          methods=['GET', 'POST'])
        self.add_url_rule('/logout', 'logout', endpoint_logout)
        self.add_url_rule('/alerts', 'alerts', self.__endpoint_alerts, methods=['GET', 'POST'])
        self.add_url_rule('/captures', 'captures', self.__endpoint_captures)
        self.add_url_rule('/doorbells', 'doorbells', self.__endpoint_doorbells)
        self.add_url_rule('/doorbells/<int:uuid>', 'doorbell', self.__endpoint_doorbell, methods=['GET', 'POST'])
        self.add_url_rule('/streams', 'streams', self.__endpoint_streams)
        self.add_url_rule('/streams/<int:uuid>', 'stream', self.__endpoint_stream)
        self.add_url_rule('/get-doorbells-info', 'get-doorbells-info', self.__endpoint_get_doorbells_info)
        self.add_url_rule('/get-new-alerts/<int:current_alert_id>', 'get-new-alerts', self.__endpoint_get_new_alerts)
        self.add_url_rule('/get-unchecked-alerts', 'get-unchecked-alerts',
                          self.__endpoint_get_unchecked_alerts)
        self.add_url_rule('/get-new-user-captures/<int:current_capture_id>', 'get-new-user-captures',
                          self.__endpoint_get_new_captures)
        self.add_url_rule('/get-new-doorbell-captures/<int:uuid>/<int:current_capture_id>', 'get-new-doorbell-captures',
                          self.__endpoint_get_new_doorbell_captures)
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
        except (Union[jwt.ExpiredSignatureError, jwt.InvalidTokenError]):
            return None

        data = self._get_user(username)
        if not data:
            return None

        session['username'] = username = data[0]
        session['name'] = data[1]
        return username

    def __convert_alert(self, alert_data: Row, need_file: bool = True):
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
            mimetype = guess_type(filename)[0] if filename else 'image/jpeg'

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

    def __convert_captures(self, captures_data: list, need_file: bool = True):
        doorbell_files = []
        for capture in captures_data:
            data = self.__convert_alert(capture, need_file)
            if not data:
                continue

            if 'message' not in data:
                tp = data['type']
                if tp == AlertType.NewBell.value:
                    nm = data['name']
                    data['message'] = f'{get_alert_type_message(tp)} ({nm})'
                else:
                    data['message'] = get_alert_type_message(data['type'])

            doorbell_files.append(data)

        return doorbell_files

    def __convert_doorbell(self, bell_data: Row or dict, get_camera: bool):
        uuid = bell_data['uuid']
        doorbell = {
            'uuid': uuid,
            'name': bell_data['name'],
            'relay': bell_data['relay'],
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

    def __get_doorbells(self, need_camera: bool):
        username = self.__authenticate()
        if not username:
            return None

        data = self._get_user_doorbells(username)
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
        return render_template('captures.html', captures=captures)

    def __endpoint_doorbells(self):
        bells = self.__get_doorbells(True)
        if bells is None:
            return redirect(url_for('login', page_to_redirect='doorbells'))

        return render_template('doorbells.html', doorbells=bells)

    def __endpoint_doorbell(self, uuid: int):
        if request.method == 'POST':
            return self.__update_doorbell(uuid)

        username = self.__authenticate()
        if not username:
            return redirect(url_for('login', page_to_redirect='doorbells'))

        if not self._check_owner(username, uuid):
            return redirect(url_for('doorbells'))

        doorbell_data = self._get_doorbell(uuid)
        doorbell = self.__convert_doorbell({'uuid': uuid, 'name': doorbell_data[0], 'relay': doorbell_data[1]}, True)
        doorbell['emails'] = doorbell_data[2]
        return render_template('doorbell.html', doorbell=doorbell)

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

    def __get_new_alerts(self, current_alert_id: int, unchecked_only: bool):
        username = self.__authenticate()
        if not username:
            return {'error': 'Unauthorized request'}, 401

        if unchecked_only:
            alerts_data = self._get_user_unchecked_alerts(username)
        else:
            alerts_data = self._get_user_alerts_after(username, current_alert_id)

        if not alerts_data:
            return {'alerts': [], 'lastAlertId': current_alert_id}, 200

        alerts = self.__convert_captures(alerts_data, False)
        if not alerts:
            return {'alerts': [], 'lastAlertId': current_alert_id}, 200

        return {'alerts': alerts, 'lastAlertId': alerts[-1]['id']}, 200

    def __endpoint_get_new_alerts(self, current_alert_id: int):
        return self.__get_new_alerts(current_alert_id, False)

    def __endpoint_get_unchecked_alerts(self):
        return self.__get_new_alerts(0, True)

    def __process_captures_request(self, captures_data: list):
        if not captures_data:
            return {'captures': [], 'lastCaptureId': 0}, 200

        captures = self.__convert_captures(captures_data)
        if not captures:
            return {'captures': [], 'lastCaptureId': 0}, 200

        return {'captures': captures, 'lastCaptureId': captures[-1]['id']}, 200

    def __endpoint_get_new_captures(self, current_capture_id: int):
        username = self.__authenticate()
        if not username:
            return {'error': 'Unauthorized request'}, 401

        captures_data = self._get_user_captures_after(username, current_capture_id)
        return self.__process_captures_request(captures_data)

    def __endpoint_get_new_doorbell_captures(self, uuid: int, current_capture_id: int):
        username = self.__authenticate()
        if not username or not self._check_owner(username, uuid):
            return {'error': 'Unauthorized request'}, 401

        captures_data = self._get_doorbell_captures_after(uuid, current_capture_id)
        return self.__process_captures_request(captures_data)

    def __endpoint_get_resource(self, filename: str):
        filename = secure_filename(filename.lower())
        filepath = path.join(self.__esp_full_path, filename)
        if not is_valid_file(filename, filepath):
            return send_from_directory(self.static_folder, 'default_profile.png'), 404

        username = self.__authenticate()
        if not username or not self._check_owner_file(username, filename):
            return self.response_class('Unauthorized request', 401)

        return send_from_directory(self.config['ESP_FILES_DIR'], filename)

    def __open_door_take_picture(self, uuid: int, alert_type: AlertType, open_door: bool):
        username = self.__authenticate()
        if not username or not self._check_owner(username, uuid):
            return {'error': 'Unauthorized request'}, 401

        esp = self.__clients.get_client(uuid)
        if not esp:
            return {'error': 'Doorbell is offline'}, 404

        if open_door:
            image, filename = esp.open_doorbell()
        else:
            image, filename = esp.save_picture()
        if not image:
            return {'error': 'Doorbell is offline'}, 404

        self.__events.on_alert(uuid, alert_type, {'filename': filename, 'image': image, 'checked': True})
        return {'filename': filename, 'mimetype': 'image/jpeg'}, 200

    def __endpoint_open_doorbell(self, uuid: int):
        return self.__open_door_take_picture(uuid, AlertType.UserPicture, True)

    def __endpoint_take_picture(self, uuid: int):
        return self.__open_door_take_picture(uuid, AlertType.UserPicture, False)

    def __endpoint_alerts(self):
        username = self.__authenticate()
        if not username:
            return redirect(url_for('login', page_to_redirect='alerts'))

        if request.method == 'POST':
            return self.__check_alerts(username)

        alerts_data = self._get_user_alerts(username)
        if not alerts_data:
            return render_template('alerts.html', last_alert_id=0)

        alerts = self.__convert_captures(alerts_data, False)
        alerts.reverse()
        return render_template('alerts.html', alerts=alerts, last_alert_id=alerts[-1]['id'])

    def __check_alerts(self, username: str):
        last_alert_id = request.form.get('last-alert-id')
        if not last_alert_id:
            return {'error': 'Invalid request'}, 400

        count = self._mark_alert_checked(username, int(last_alert_id))
        return {'alertsMarked': count, 'last-alert-id': last_alert_id}, 200
