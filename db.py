import sqlite3


def singleton(cls):
    _instance = {}

    def inner(*args, **kwargs):
        if cls not in _instance:
            _instance[cls] = cls(*args, **kwargs)
        return _instance[cls]

    return inner


@singleton
class LiteDB:
    def __init__(self, filename):
        self.filename = filename
        self.conn = sqlite3.connect(self.filename)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        self.conn.close()

    def execute(self, sql, values=None):
        try:
            if values is None:
                self.conn.execute(sql)
            else:
                if type(values) is list:
                    self.conn.executemany(sql, values)
                else:
                    self.conn.execute(sql, values)
            count = self.conn.total_changes
            self.conn.commit()
        except Exception as e:
            return False, e
        if count > 0:
            return True
        else:
            return False

    def counts(self, table):
        if table is None:
            return 0
        else:
            return self.conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]

    def get_paginated_data(self, page: int, table: str, page_size: int = 100):
        offset = (page - 1) * page_size
        data = self.conn.execute(f'SELECT * FROM {table} LIMIT {page_size} OFFSET {offset}').fetchall()
        return data

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
