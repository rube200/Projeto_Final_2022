import logging as log
from collections import namedtuple
from io import BytesIO
from os import environ
from sqlite3 import connect as sql_connect, PARSE_DECLTYPES, Row as sqlRow
from time import sleep, monotonic
from traceback import format_exc

import bcrypt
import jwt
from flask import abort, current_app, Flask, g, redirect, render_template, request, send_file, url_for, \
    stream_with_context, session, flash
from flask_mail import Mail, Message

from esp_socket.socket_client import SocketClient
from esp_socket.socket_events import SocketEvents

NAV_DICT = [
    {'id': 'doorbells', 'title': 'Manage Doorbells', 'icon': 'bi-book-fill', 'url': 'doorbells'},
    {'id': 'all_streams', 'title': 'All Streams', 'icon': 'bi-cast', 'url': 'all_streams'},
    {'id': 'notifications', 'title': 'Notificationss', 'icon': 'bi-globe', 'url': 'images'},
    {'id': 'statistics', 'title': 'Statistics', 'icon': 'bi-bar-chart-fill', 'url': 'doorbells'},
]


class WebServer(Flask):
    def __init__(self, _esp_clients: dict = None):
        super(WebServer, self).__init__(import_name=__name__)
        self.__esp_clients = _esp_clients or {}
        self.__events = None

        self.config.from_pyfile('flask.cfg')
        self.config['DATABASE'] = self.__db_config = environ.get('DATABASE') or 'esp32cam.sqlite'
        if self.config.get('RANDOM_SECRET_KEY'):
            import secrets
            self.config['JWT_SECRET_KEY'] = secrets.token_hex(32)
            self.config['SECRET_KEY'] = secrets.token_hex(32)
        self.__mail = Mail(self)

    @property
    def esp_clients(self) -> dict:
        return dict(self.__esp_clients)

    @esp_clients.setter
    def esp_clients(self, value: dict) -> None:
        self.__esp_clients = value

    def get_client(self, esp_id: int) -> SocketClient:
        return self.__esp_clients.get(esp_id)

    def setup_events(self, events: SocketEvents) -> None:
        self.__events = events
        self.__events.on_bell_pressed += self.__on_bell_pressed
        self.__events.on_motion_detected += self.__on_motion_detected

    def open_relay(self, esp_id):
        self.__events.on_open_relay_requested(esp_id)

    def __get_mail_by_esp(self, esp_id: int) -> str or None:
        try:
            sql_con = sql_connect(self.__db_config, detect_types=PARSE_DECLTYPES)
            sql_con.row_factory = sqlRow
            cursor = sql_con.cursor()
            try:
                cursor.execute(
                    'SELECT u.email FROM user u INNER JOIN doorbell d on u.username = d.owner WHERE d.id = ?', [esp_id])
                row = cursor.fetchone()
                if not row:
                    return None

                return row[0]

            finally:
                cursor.close()
                sql_con.close()
        except Exception as ex:
            log.error(f'Exception while getting email for esp_id {esp_id}: {ex!r}')
            return None

    def __on_bell_pressed(self, client: SocketClient):
        email = self.__get_mail_by_esp(client.uuid)
        if not email:
            return

        self.__mail.send(Message('Doorbell pressed', [email], 'GOT CHECK IT NOW. MOTHERFUCKER'))

    def __on_motion_detected(self, client: SocketClient):
        email = self.__get_mail_by_esp(client.uuid)
        if not email:
            return

        self.__mail.send(Message('Motion detected', [email], 'GOT CHECK IT NOW. MOTHERFUCKER'))


web = WebServer()


def init_db(wb: WebServer) -> None:
    with wb.app_context():
        db = get_db()

        with current_app.open_resource(current_app.config['SCHEMA_FILE']) as f:
            db.cursor().executescript(f.read().decode('utf-8'))

        db.commit()
        close_db(None)


def get_db():
    if 'db' in g:
        return g.db

    g.db = sql_connect(current_app.config['DATABASE'], detect_types=PARSE_DECLTYPES)
    g.db.row_factory = sqlRow
    return g.db


# noinspection PyUnusedLocal
@web.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db:
        db.close()


init_db(web)


@web.context_processor
def inject_nav():
    return dict(nav=NAV_DICT)


# noinspection PyUnusedLocal
@web.errorhandler(404)
def page_not_found(e):
    return redirect(url_for('index'))


# noinspection PyUnusedLocal
@web.errorhandler(400)
def invalid_request(e):
    return redirect(url_for('index'))


def get_token(user_id):
    return jwt.encode(
        {
            'user_id': user_id,
        },
        current_app.config['JWT_SECRET_KEY'],
        'HS256'
    )


def authenticate() -> (None or int):
    token = session.get('token')
    user_id = session.get('user_id')
    print("user id is: "+ str(user_id))
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
        return render_template('login.html')

    usr = request.form.get('username')
    pwd = request.form.get('password')
    if not usr or not pwd:
        flash('Invalid form input.', 'danger')
        return render_template('login.html')

    cursor = get_db().cursor()
    try:
        cursor.execute('SELECT username, name, password FROM user WHERE username = ?', [usr]),
        db_row = cursor.fetchone()
    finally:
        cursor.close()
    if not db_row or not db_row[0] or not db_row[2] or not bcrypt.checkpw(pwd.encode('utf-8'), db_row[2]):
        flash('Invalid credentials.', 'danger')
        return render_template('login.html')

    return redirect_to_doorbells(db_row[0], db_row[1])


@web.route('/register', methods=['GET', 'POST'])
def register():
    if authenticate():
        return redirect(url_for('doorbells'))

    if request.method == 'GET':
        return render_template('register.html')

    usr = request.form.get('username')
    email = request.form.get('email')
    pwd = request.form.get('password')
    if not usr or not email or not pwd:
        flash('Invalid form input.', 'danger')
        return render_template('register.html')

    hash_pwd = bcrypt.hashpw(pwd.encode('utf-8'), bcrypt.gensalt())

    con = get_db()
    cursor = con.cursor()
    try:
        cursor.execute('INSERT OR IGNORE INTO user (username, email, password, name) VALUES (?, ?, ?, ?)',
                       (usr, email, hash_pwd, usr))
        con.commit()
        if cursor.rowcount < 1:
            flash('Username or email already taken.', 'danger')
            return render_template('register.html')

        # username sanitize
        cursor.execute('SELECT username, name FROM user WHERE username = ?', [usr])
        db_row = cursor.fetchone()
    finally:
        cursor.close()

    if not db_row or not db_row[0]:
        flash('Something went wrong, try again.', 'danger')
        return render_template('register.html')

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

    return render_template('doorbells.html', doorbells=bells)


@web.route('/all_streams')
def all_streams():
    bells = get_doorbells_data()
    if bells is None:
        return redirect(url_for('index'))

    return render_template('all_streams.html', doorbells=bells)


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

@web.route('/images')
def images():
    if authenticate():
        #add dtQuery for notificationss here

        cursor = get_db().cursor()
        try:
            #cursor.execute("SELECT notifications.TYPE, notifications.PATH, notifications.DATE, DOORBELL.NAME FROM notifications JOIN DOORBELL ON notifications.DOORBELL_ID = DOORBELL.ID join user on user.name WHERE DOORBELL.owner  LIKE ? order by notifications.DATE desc", (user,))
            cursor.execute("SELECT notifications.PATH, notifications.time, doorbell.name FROM notifications JOIN doorbell ON notifications.esp_id = doorbell.id WHERE doorbell.owner LIKE ? and notifications.type not like 0 order by notifications.time desc", [session.get('user_id'),])
            db_rows = cursor.fetchall()
            #types = []
            paths = []
            names = []
            dates = []
            for bell in db_rows:
                #types.append(bell[0])
                paths.append(bell[1])
                dates.append(bell[2].split(".")[0]) #split to remove miliseconds
                names.append(bell[3])

            #return render_template('imageGal.html', types = types, paths = paths, dates = dates, doorbells = names)
            return render_template('imageGal.html', paths = paths, dates = dates, doorbells = names)

        finally:
            cursor.close()

    return redirect(url_for('login'))

@web.route('/bell')
def doorbellTest():
    return render_template('doorbell.html')