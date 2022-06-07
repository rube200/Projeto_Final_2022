from sqlite3 import connect as sql_connect, PARSE_DECLTYPES, Row as sqlRow


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
