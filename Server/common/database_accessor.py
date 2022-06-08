from sqlite3 import connect as sql_connect, PARSE_DECLTYPES, Row as sqlRow
from typing import Tuple

import bcrypt


class DatabaseAccessor:
    def __init__(self, database):
        self.__db = database

    def __del__(self):
        del self.__db

    def __get_connection(self):
        sql_con = sql_connect(self.__db, detect_types=PARSE_DECLTYPES)
        sql_con.row_factory = sqlRow
        return sql_con

    def __get_owner(self, uuid: int) -> str or None:
        con = self.__get_connection()
        cursor = con.cursor()
        try:
            cursor.execute('SELECT owner FROM doorbell WHERE id = ? LIMIT 1', [uuid])
            data = cursor.fetchone()
            return data[0] if data else None
        finally:
            cursor.close()
            con.close()

    def __register_doorbell(self, username: str, uuid: int) -> bool:
        con = self.__get_connection()
        cursor = con.cursor()
        try:
            cursor.execute('SELECT 1 FROM user WHERE username = ? LIMIT 1', [username])
            data = cursor.fetchone()
            if not data or not data[0]:
                return False

            cursor.execute('INSERT OR IGNORE INTO doorbell(id, name, owner) VALUES (?, ?, ?)', [uuid, uuid, username])
            con.commit()
            if cursor.rowcount > 0:
                return True

            cursor.execute('SELECT 1 FROM doorbell WHERE id = ? LIMIT 1', [uuid])
            data = cursor.fetchone()
            return data and data[0]
        finally:
            cursor.close()
            con.close()

    def __add_notification(self, uuid, notification_type, path) -> None:
        con = self.__get_connection()
        cursor = con.cursor()
        try:
            cursor.execute('INSERT INTO notifications(esp_id, type, path) VALUES (?, ?, ?)',
                           [uuid, notification_type, path])
            con.commit()
        finally:
            cursor.close()
            con.close()

    def __get_owner_email(self, esp_id: int) -> str or None:
        con = self.__get_connection()
        cursor = con.cursor()
        try:
            cursor.execute(
                'SELECT u.email FROM user u INNER JOIN doorbell d on u.username = d.owner WHERE d.id = ? LIMIT 1',
                [esp_id])
            data = cursor.fetchone()
            return data[0] if data else None
        finally:
            cursor.close()
            con.close()

    def __check_owner(self, username: str, uuid: int) -> bool:
        con = self.__get_connection()
        cursor = con.cursor()
        try:
            cursor.execute('SELECT 1 FROM doorbell WHERE id = ? and owner = ? LIMIT 1', [uuid, username])
            data = cursor.fetchone()
            return data and data[0]
        finally:
            cursor.close()
            con.close()

    def __get_user_by_username(self, username: str) -> Tuple[str, str] or None:
        con = self.__get_connection()
        cursor = con.cursor()
        try:
            cursor.execute('SELECT username, name FROM user WHERE username = ? LIMIT 1', [username])
            data = cursor.fetchone()
            return data[0], data[1] if data else None
        finally:
            cursor.close()
            con.close()

    def __try_login_user(self, username: str, password: str) -> Tuple[str, str] or None:
        con = self.__get_connection()
        cursor = con.cursor()
        try:
            cursor.execute('SELECT username, name, password FROM user WHERE username = ? LIMIT 1', [username])
            data = cursor.fetchone()
        finally:
            cursor.close()
            con.close()

        if not data:
            return None

        usr = data[0]
        name = data[1]
        pwd = data[2]
        if not usr or not name or not pwd or not bcrypt.checkpw(password.encode('utf-8'), pwd):
            return None

        return usr, name

    def __try_register_user(self, username: str, email: str, password: bytes) -> Tuple[str, str] or None:
        con = self.__get_connection()
        cursor = con.cursor()
        try:
            cursor.execute('INSERT OR IGNORE INTO user (username, email, password, name) VALUES (?, ?, ?, ?)',
                           [username, email, password, username])
            con.commit()

            if cursor.rowcount < 1:
                return None

            cursor.execute('SELECT username, name FROM user WHERE username = ?', [username])
            data = cursor.fetchone()
            return data[0], data[1] if data else None
        finally:
            cursor.close()
            con.close()

    def __get_doorbells_by_owner(self, username):
        con = self.__get_connection()
        cursor = con.cursor()
        try:
            cursor.execute('SELECT id, name FROM doorbell WHERE owner = ?', [username]),
            data = cursor.fetchall()
        finally:
            cursor.close()
            con.close()
