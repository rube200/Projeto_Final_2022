from sqlite3 import connect as sql_connect, PARSE_DECLTYPES, Row as sqlRow
from typing import List, Tuple

import bcrypt

from common.alert_type import AlertType

alerts_columns = ['uuid', 'type', 'time', 'checked', 'filename', 'notes']


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
            cursor.execute('SELECT owner '
                           'FROM doorbell '
                           'WHERE id = ? '
                           'LIMIT 1',
                           [uuid])
            data = cursor.fetchone()
            return data['owner'] if data else None
        finally:
            cursor.close()
            con.close()

    def _register_doorbell(self, username: str, uuid: int) -> bool:
        username = username.upper()
        con = self._get_connection()
        cursor = con.cursor()
        try:
            cursor.execute('SELECT 1 '
                           'FROM user '
                           'WHERE username = ? '
                           'LIMIT 1',
                           [username])
            data = cursor.fetchone()
            if not data or not data[0]:
                return False

            cursor.execute('INSERT OR IGNORE INTO doorbell(id, name, owner) '
                           'VALUES (?, ?, ?)',
                           [uuid, uuid, username])
            cursor.execute('INSERT OR IGNORE INTO doorbell_alerts '
                           'SELECT ?, email '
                           'FROM user '
                           'WHERE username = ?',
                           [uuid, username])
            con.commit()
            if cursor.rowcount > 0:
                return True

            cursor.execute('SELECT 1 '
                           'FROM doorbell '
                           'WHERE id = ? '
                           'LIMIT 1',
                           [uuid])
            data = cursor.fetchone()
            return data and data[0]
        finally:
            cursor.close()
            con.close()

    def _add_alert(self, info: dict) -> None:
        columns = []
        values = []
        for k in alerts_columns:
            v = info.get(k)
            if not v:
                continue

            columns.append(k)
            values.append(v)

        columns_placer = ', '.join(columns)
        values_placer = ', '.join(['?'] * len(values))

        con = self._get_connection()
        cursor = con.cursor()
        try:
            # noinspection SqlInsertValues
            cursor.execute(f'INSERT INTO alerts({columns_placer}) '
                           f'VALUES ({values_placer})',
                           values)
            con.commit()
        finally:
            cursor.close()
            con.close()

    def _get_doorbell_name(self, uuid: int) -> str or None:
        con = self._get_connection()
        cursor = con.cursor()
        try:
            cursor.execute(
                'SELECT name '
                'FROM doorbell '
                'WHERE id = ? '
                'LIMIT 1',
                [uuid])
            data = cursor.fetchone()
            return data['name'] if data else None
        finally:
            cursor.close()
            con.close()

    def _get_alert_emails(self, uuid: int) -> str or None:
        con = self._get_connection()
        cursor = con.cursor()
        try:
            cursor.execute(
                'SELECT email '
                'FROM doorbell_alerts '
                'WHERE uuid = ?',
                [uuid])
            data = cursor.fetchall()
            return [d['email'] for d in data] if data else []
        finally:
            cursor.close()
            con.close()

    def _check_owner(self, username: str, uuid: int) -> bool:
        con = self._get_connection()
        cursor = con.cursor()
        try:
            cursor.execute('SELECT 1 '
                           'FROM doorbell '
                           'WHERE id = ? '
                           'AND owner = ? '
                           'LIMIT 1',
                           [uuid, username.upper()])
            data = cursor.fetchone()
            return data and data[0]
        finally:
            cursor.close()
            con.close()

    def _check_owner_file(self, username: str, filename: str) -> bool:
        con = self._get_connection()
        cursor = con.cursor()
        try:
            cursor.execute('SELECT 1 '
                           'FROM alerts a '
                           'INNER JOIN doorbell d '
                           'ON a.uuid = d.id '
                           'WHERE a.filename = ? '
                           'AND d.owner = ? '
                           'LIMIT 1',
                           [filename.lower(), username.upper()])
            data = cursor.fetchone()
            return data and data[0]
        finally:
            cursor.close()
            con.close()

    def _get_user(self, username: str) -> Tuple[str, str] or None:
        con = self._get_connection()
        cursor = con.cursor()
        try:
            cursor.execute('SELECT username, name '
                           'FROM user '
                           'WHERE username = ? '
                           'LIMIT 1',
                           [username.upper()])
            data = cursor.fetchone()
            return data['username'], data['name'] if data else None
        finally:
            cursor.close()
            con.close()

    def _try_login(self, username: str, password: str) -> Tuple[str, str] or None:
        con = self._get_connection()
        cursor = con.cursor()
        try:
            cursor.execute('SELECT username, name, password '
                           'FROM user '
                           'WHERE username = ? '
                           'LIMIT 1',
                           [username.upper()])
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

    def _try_register(self, username: str, email: str, password: bytes) -> Tuple[str, str] or None:
        username = username.upper()
        con = self._get_connection()
        cursor = con.cursor()
        try:
            cursor.execute('INSERT OR IGNORE INTO user (username, email, password, name) '
                           'VALUES (?, ?, ?, ?)',
                           [username, email.lower(), password, username])
            con.commit()
            if cursor.rowcount < 1:
                return None

            cursor.execute('SELECT username, name '
                           'FROM user '
                           'WHERE username = ?',
                           [username])
            data = cursor.fetchone()
            return data['username'], data['name'] if data else None
        finally:
            cursor.close()
            con.close()

    def _get_doorbells(self, username: str):
        con = self._get_connection()
        cursor = con.cursor()
        try:
            cursor.execute('SELECT id, name '
                           'FROM doorbell '
                           'WHERE owner = ?',
                           [username.upper()]),
            return cursor.fetchall()
        finally:
            cursor.close()
            con.close()

    def _get_alerts_count(self, username: str):
        con = self._get_connection()
        cursor = con.cursor()
        try:
            cursor.execute('SELECT COUNT(*) '
                           'FROM alerts a '
                           'INNER JOIN doorbell d '
                           'ON a.uuid = d.id '
                           'WHERE NOT a.checked '
                           'AND d.owner = ?',
                           [username.upper()])
            return cursor.fetchone()[0]
        finally:
            cursor.close()
            con.close()

    def _get_user_captures(self, username: str):
        con = self._get_connection()
        cursor = con.cursor()
        try:
            cursor.execute(f'SELECT d.id, d.name, a.id, a.time, a.type, a.filename '
                           f'FROM alerts a '
                           f'INNER JOIN doorbell d '
                           f'ON a.uuid = d.id '
                           f'WHERE a.filename IS NOT NULL '
                           f'AND a.type IN (?, ?, ?) '
                           f'AND d.owner = ? '
                           f'ORDER BY a.time DESC',
                           [AlertType.Bell.value, AlertType.Movement.value, AlertType.UserPicture.value,
                            username.upper()])
            return cursor.fetchall()
        finally:
            cursor.close()
            con.close()

    def _get_doorbell_alerts(self, uuid: int, types: List[AlertType] = None, exclude_checked: bool = True):
        if types:
            t = [t.value for t in types]
        else:
            t = []
        con = self._get_connection()
        cursor = con.cursor()
        try:
            cmd = f'SELECT a.id, a.time, a.type, a.filename, a.notes ' \
                  f'FROM alerts a ' \
                  f'WHERE a.uuid = ?'

            if exclude_checked:
                cmd += ' AND NOT a.checked'

            size = len(t)
            if size > 0:
                cmd += f' AND a.type IN ({", ".join(["?"] * size)})'
            cmd += f' ORDER BY a.time DESC'

            t.insert(0, uuid)
            cursor.execute(cmd, t)
            return cursor.fetchall()
        finally:
            cursor.close()
            con.close()

    def _get_doorbell(self, uuid: int):
        con = self._get_connection()
        cursor = con.cursor()
        try:
            cursor.execute('SELECT name '
                           'FROM doorbell '
                           'WHERE id = ?',
                           [uuid]),
            data = cursor.fetchone()
            name = data['name'] if data else uuid

            cursor.execute('SELECT email '
                           'FROM doorbell_alerts '
                           'WHERE uuid = ?',
                           [uuid]),
            data = cursor.fetchall()
            emails = [d['email'] for d in data] if data else []
            return name, emails
        finally:
            cursor.close()
            con.close()

    def _doorbell_update(self, username: str, password: str, uuid: int, doorbell_name: str,
                         alert_emails: List[str]) -> bool:
        if not self._try_login(username, password):
            return False

        con = self._get_connection()
        cursor = con.cursor()
        try:
            cursor.execute('UPDATE doorbell '
                           'SET name = ? '
                           'WHERE id = ?',
                           [doorbell_name, uuid])
            cursor.execute('DELETE FROM doorbell_alerts '
                           'WHERE uuid = ?',
                           [uuid])
            if len(alert_emails):
                cursor.executemany('INSERT INTO doorbell_alerts '
                                   'VALUES (?, ?)',
                                   zip([uuid] * len(alert_emails), alert_emails))

            con.commit()
            return True
        finally:
            cursor.close()
            con.close()
