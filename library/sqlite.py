import sqlite3
from contextlib import contextmanager
from pathlib import Path


class SQLite:
    """ Компактная встраиваемая СУБД """

    def __init__(self,
                 filepath: Path,  # Путь к файлу БД
                 init_stmt: str = ""  # Запрос для создания таблиц
                 ) -> None:

        self.filepath = filepath

        if init_stmt and not filepath.exists():
            with self.connection() as conn:
                for stmt in init_stmt.split(";"):
                    conn.execute(stmt)

    @contextmanager
    def connection(self) -> sqlite3.Connection:
        """ Основной метод соединения с БД """

        conn = None
        try:
            with self._connect() as conn:
                yield conn
        except:
            raise
        finally:
            if isinstance(conn, sqlite3.Connection):
                conn.close()

    def _connect(self) -> sqlite3.Connection:
        """ Соединение с БД с помощью библиотеки sqlite3 """

        def dict_factory(cursor, row) -> dict:
            return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

        conn = sqlite3.connect(self.filepath, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = dict_factory
        return conn
