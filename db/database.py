import libsql
import streamlit as st


# --- Wrapper classes to provide dict-like row access (libsql lacks row_factory) ---

class DictRow:
    """Row that supports row['column'], dict(row), and iteration over keys."""

    def __init__(self, columns, values):
        self._data = dict(zip(columns, values))

    def __getitem__(self, key):
        if isinstance(key, str):
            return self._data[key]
        return list(self._data.values())[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()


class DictCursor:
    """Wraps a libsql cursor to return DictRow objects."""

    def __init__(self, cursor):
        self._cursor = cursor

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def description(self):
        return self._cursor.description

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        columns = [desc[0] for desc in self._cursor.description]
        return DictRow(columns, row)

    def fetchall(self):
        rows = self._cursor.fetchall()
        if not rows:
            return []
        columns = [desc[0] for desc in self._cursor.description]
        return [DictRow(columns, row) for row in rows]


class ConnectionWrapper:
    """Wraps a libsql connection so all queries return DictRow objects."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=None):
        if params:
            cursor = self._conn.execute(sql, params)
        else:
            cursor = self._conn.execute(sql)
        return DictCursor(cursor)

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


# --- Schema ---

SCHEMA_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        username      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
        password_hash TEXT    NOT NULL,
        salt          TEXT    NOT NULL,
        created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS transactions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL,
        ticker      TEXT    NOT NULL,
        type        TEXT    NOT NULL CHECK(type IN ('BUY', 'SELL')),
        shares      REAL    NOT NULL CHECK(shares > 0),
        price       REAL    NOT NULL CHECK(price > 0),
        date        TEXT    NOT NULL,
        notes       TEXT    DEFAULT '',
        created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
        updated_at  TEXT    NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_transactions_ticker ON transactions(ticker)",
    "CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)",
    "CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)",
]


def get_connection() -> ConnectionWrapper:
    url = st.secrets["TURSO_DATABASE_URL"]
    token = st.secrets["TURSO_AUTH_TOKEN"]
    conn = libsql.connect(url, auth_token=token)
    return ConnectionWrapper(conn)


def init_db():
    conn = get_connection()
    for stmt in SCHEMA_STATEMENTS:
        conn.execute(stmt)
    conn.commit()
    conn.close()
