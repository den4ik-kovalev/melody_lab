import sqlite3

import jsonpickle

import config
from library.sqlite import SQLite


def setup_custom_types() -> (type, type):
    """ Пользовательские типы данных для сохранения в БД """

    from library.node_editor import NodeFreezer
    from melody import Melody

    def adapt_pyobject(obj: object) -> bytes:
        return jsonpickle.encode(obj)

    def convert_pyobject(s: bytes) -> object:
        return jsonpickle.decode(s)

    sqlite3.register_adapter(NodeFreezer.EditorState, adapt_pyobject)
    sqlite3.register_converter("PYOBJECT", convert_pyobject)
    sqlite3.register_adapter(Melody, adapt_pyobject)
    sqlite3.register_converter("PYOBJECT", convert_pyobject)

    return NodeFreezer.EditorState, Melody


NodeEditorState, Melody = setup_custom_types()


class Database(SQLite):

    def insert_preset(self, name: str, state: NodeEditorState) -> int:
        """ Добавить запись в таблицу preset """

        with self.connection() as conn:

            stmt = "INSERT INTO preset(name, state) VALUES (?, ?)"
            values = (name, state)
            conn.execute(stmt, values)

            stmt = "SELECT last_insert_rowid() AS rowid"
            cur = conn.execute(stmt)
            return cur.fetchone()["rowid"]

    def select_presets_info(self) -> list[dict]:
        """ Получить инфу о сохраненных состояниях preset """

        with self.connection() as conn:
            stmt = "SELECT rowid, name FROM preset"
            cur = conn.execute(stmt)
            return cur.fetchall()

    def select_preset(self, rowid: int) -> list[dict]:
        """ Получить одну запись из preset """

        with self.connection() as conn:
            stmt = "SELECT * FROM preset WHERE rowid = ?"
            cur = conn.execute(stmt, (rowid,))
            return cur.fetchone()

    def delete_preset(self, rowid: int):
        """ Удалить одну запись из preset """

        with self.connection() as conn:
            stmt = "DELETE FROM preset WHERE rowid = ?"
            conn.execute(stmt, (rowid,))

    def insert_melody(self, name: str, melody: Melody) -> int:
        """ Добавить записи в таблицу melody """

        with self.connection() as conn:
            stmt = """
               INSERT INTO melody(name, obj, length, duration, grid_size) 
               VALUES (?, ?, ?, ?, ?)
               """
            values = (name, melody, melody.length, melody.duration.quarterLength, melody.grid_size)
            conn.execute(stmt, values)

            stmt = "SELECT last_insert_rowid() AS rowid"
            cur = conn.execute(stmt)
            return cur.fetchone()["rowid"]

    def select_melodies_info(self) -> list[dict]:
        """ Получить инфу о мелодиях из melody """

        with self.connection() as conn:
            stmt = "SELECT rowid, name, length, duration, grid_size, favorite FROM melody"
            cur = conn.execute(stmt)
            return cur.fetchall()

    def select_melody(self, rowid: int) -> list[dict]:
        """ Получить одну запись из melody """

        with self.connection() as conn:
            stmt = "SELECT * FROM melody WHERE rowid = ?"
            cur = conn.execute(stmt, (rowid,))
            return cur.fetchone()

    def switch_melody_favorite(self, rowid: int):
        """ Поменять значение melody.favorite на противоположное """

        with self.connection() as conn:
            stmt = "UPDATE melody SET favorite = NOT favorite WHERE rowid = ?"
            conn.execute(stmt, (rowid,))

    def delete_melody(self, rowid: int):
        """ Удалить запись из melody """

        with self.connection() as conn:
            stmt = "DELETE FROM melody WHERE rowid = ?"
            conn.execute(stmt, (rowid,))


# запрос для инициализации таблиц БД
INIT_STMT = """
CREATE TABLE IF NOT EXISTS preset (
    name TEXT,
    state PYOBJECT
);
CREATE TABLE IF NOT EXISTS melody (
    name TEXT,
    obj PYOBJECT,
    length INT,
    duration REAL,
    grid_size REAL,
    favorite INT DEFAULT 0
)
"""

db = Database(
    filepath=(config.app_dir / "main.db"),
    init_stmt=INIT_STMT
)
