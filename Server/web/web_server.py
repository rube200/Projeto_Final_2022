import logging as log
from os import environ

import jwt
from flask import Flask, redirect, url_for, current_app
from flask_mail import Mail, Message

from common.database_accessor import DatabaseAccessor
from common.esp_client import EspClient
from common.esp_clients import EspClients
from common.notification_type import NotificationType
from socket_common.socket_events import SocketEvents

NAV_DICT = [
    {'id': 'doorbells', 'title': 'Manage Doorbells', 'icon': 'bi-book-fill', 'url': 'doorbells'},
    {'id': 'all_streams', 'title': 'All Streams', 'icon': 'bi-cast', 'url': 'all_streams'},
    {'id': 'pictures', 'title': 'Pictures', 'icon': 'bi-globe', 'url': 'doorbells'},
    {'id': 'statistics', 'title': 'Statistics', 'icon': 'bi-bar-chart-fill', 'url': 'doorbells'},
]


class WebServer(DatabaseAccessor, Flask):
    def __init__(self, clients: EspClients, events: SocketEvents):
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

    def __gen_token(self, user_id: str):
        return jwt.encode(
            {
                'user_id': user_id,
            },
            current_app.config['JWT_SECRET_KEY'],
            'HS256'
        )

    def __setup_db(self):
        con = self.__get_connection()
        cursor = con.cursor()

        with current_app.open_resource(current_app.config['SCHEMA_FILE']) as f:
            cursor.executescript(f.read().decode('utf-8'))
        con.commit()

        cursor.close()
        con.close()

    def __setup_web(self):
        self.register_error_handler(400, lambda e: redirect(url_for('index')))
        self.register_error_handler(404, lambda e: redirect(url_for('index')))
        self.template_context_processors[None].append(lambda: dict(nav=NAV_DICT))
