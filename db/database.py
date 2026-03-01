import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "portfolio.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT    NOT NULL,
    salt          TEXT    NOT NULL,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS transactions (
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
);

CREATE INDEX IF NOT EXISTS idx_transactions_ticker ON transactions(ticker);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _migrate_db(conn: sqlite3.Connection):
    """Handle schema migrations for existing databases."""
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if cursor.fetchone() is None:
        # Users table doesn't exist yet — create it
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT    NOT NULL,
                salt          TEXT    NOT NULL,
                created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)

    # Check if transactions table has user_id column
    cols = [row["name"] for row in conn.execute("PRAGMA table_info(transactions)").fetchall()]
    if "user_id" not in cols:
        # Add user_id column with a default of 0 (legacy data)
        conn.execute("ALTER TABLE transactions ADD COLUMN user_id INTEGER NOT NULL DEFAULT 0")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)")

    conn.commit()


def init_db():
    conn = get_connection()
    # Check if transactions table already exists (existing DB)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'")
    if cursor.fetchone() is not None:
        # Existing database — run migrations
        _migrate_db(conn)
    else:
        # Fresh database — create full schema
        conn.executescript(SCHEMA_SQL)
    conn.close()
