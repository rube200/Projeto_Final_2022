from sqlite3 import connect as sql_connect, PARSE_DECLTYPES, Row as sqlRow
from typing import Tuple

import bcrypt

from common.notification_type import NotificationType


class DatabaseAccessor:
    def __init__(self, database):
        self.__db = database

    def __del__(self):
        del self.__db

    def _get_connection(self):
        sql_con = sql_connect(self.__db, detect_types=PARSE_DECLTYPES)
        sql_con.row_factory = sqlRow
        return sql_con

    def _get_owner(self, uuid: int) -> str or None:
        con = self._get_connection()
        cursor = con.cursor()
        try:
            cursor.execute('SELECT owner FROM doorbell WHERE id = ? LIMIT 1', [uuid])
            data = cursor.fetchone()
            return data['owner'] if data else None
        finally:
            cursor.close()
            con.close()

    def _register_doorbell(self, username: str, uuid: int) -> bool:
        con = self._get_connection()
        cursor = con.cursor()
        try:
            cursor.execute('SELECT 1 FROM user WHERE username = ? LIMIT 1', [username.upper()])
            data = cursor.fetchone()
            if not data or not data[0]:
                return False

            cursor.execute('INSERT OR IGNORE INTO doorbell(id, name, owner) VALUES (?, ?, ?)',
                           [uuid, uuid, username.upper()])
            con.commit()
            if cursor.rowcount > 0:
                return True

            cursor.execute('SELECT 1 FROM doorbell WHERE id = ? LIMIT 1', [uuid])
            data = cursor.fetchone()
            return data and data[0]
        finally:
            cursor.close()
            con.close()

    def _add_notification(self, uuid: int, notification_type: NotificationType, path: str) -> None:
        con = self._get_connection()
        cursor = con.cursor()
        try:
            cursor.execute('INSERT INTO notifications(uuid, type, path) VALUES (?, ?, ?)',
                           [uuid, notification_type.value, path])
            con.commit()
        finally:
            cursor.close()
            con.close()

    def _get_owner_email(self, uuid: int) -> str or None:
        con = self._get_connection()
        cursor = con.cursor()
        try:
            cursor.execute(
                'SELECT u.email FROM user u INNER JOIN doorbell d on u.username = d.owner WHERE d.id = ? LIMIT 1',
                [uuid])
            data = cursor.fetchone()
            return data['email'] if data else None
        finally:
            cursor.close()
            con.close()

    def _check_owner(self, username: str, uuid: int) -> bool:
        con = self._get_connection()
        cursor = con.cursor()
        try:
            cursor.execute('SELECT 1 FROM doorbell WHERE id = ? and owner = ? LIMIT 1', [uuid, username.upper()])
            data = cursor.fetchone()
            return data and data[0]
        finally:
            cursor.close()
            con.close()

    def _get_user_by_username(self, username: str) -> Tuple[str, str] or None:
        con = self._get_connection()
        cursor = con.cursor()
        try:
            cursor.execute('SELECT username, name FROM user WHERE username = ? LIMIT 1', [username.upper()])
            data = cursor.fetchone()
            return data['username'], data['name'] if data else None
        finally:
            cursor.close()
            con.close()

    def _try_login_user(self, username: str, password: str) -> Tuple[str, str] or None:
        con = self._get_connection()
        cursor = con.cursor()
        try:
            cursor.execute('SELECT username, name, password FROM user WHERE username = ? LIMIT 1', [username.upper()])
            data = cursor.fetchone()
        finally:
            cursor.close()
            con.close()

        if not data:
            return None

        usr = data['username']
        name = data['name']
        pwd = data['password']
        if not usr or not name or not pwd or not bcrypt.checkpw(password.encode('utf-8'), pwd):
            return None

        return usr, name

    def _try_register_user(self, username: str, email: str, password: bytes) -> Tuple[str, str] or None:
        con = self._get_connection()
        cursor = con.cursor()
        try:
            cursor.execute('INSERT OR IGNORE INTO user (username, email, password, name) VALUES (?, ?, ?, ?)',
                           [username.upper(), email.upper(), password, username])
            con.commit()

            if cursor.rowcount < 1:
                return None

            cursor.execute('SELECT username, name FROM user WHERE username = ?', [username.upper()])
            data = cursor.fetchone()
            return data['username'], data['name'] if data else None
        finally:
            cursor.close()
            con.close()

    def _get_doorbells_by_owner(self, username: str):
        con = self._get_connection()
        cursor = con.cursor()
        try:
            cursor.execute('SELECT id, name FROM doorbell WHERE owner = ?', [username.upper()]),
            return cursor.fetchall()
        finally:
            cursor.close()
            con.close()

    def _get_notifications_by_username(self, username: str, exclude_checked: bool = True):
        con = self._get_connection()
        cursor = con.cursor()
        try:
            cursor.execute(
                f'SELECT n.id, d.name, n.time, n.type, n.path{", n.checked " if not exclude_checked else " "}'
                'FROM notifications n '
                'INNER JOIN doorbell d '
                f'ON {"NOT n.checked AND" if exclude_checked else ""} n.uuid = d.id '
                f'WHERE d.owner = ?',
                [username.upper()]),
            return cursor.fetchall()
        finally:
            cursor.close()
            con.close()
