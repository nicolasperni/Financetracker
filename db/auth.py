import hashlib
import os
from db.database import get_connection


def _hash_password(password: str, salt: bytes) -> str:
    """Hash a password with the given salt using SHA-256."""
    return hashlib.sha256(salt + password.encode("utf-8")).hexdigest()


def create_user(username: str, password: str) -> int:
    """Create a new user. Returns the user ID.

    Raises ValueError if username is already taken or inputs are invalid.
    """
    username = username.strip()
    if not username:
        raise ValueError("Username cannot be empty.")
    if len(username) < 3:
        raise ValueError("Username must be at least 3 characters.")
    if len(password) < 4:
        raise ValueError("Password must be at least 4 characters.")

    salt = os.urandom(32)
    password_hash = _hash_password(password, salt)

    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
            (username, password_hash, salt.hex()),
        )
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        if "UNIQUE constraint" in str(e):
            raise ValueError(f"Username '{username}' is already taken.")
        raise
    finally:
        conn.close()


def authenticate(username: str, password: str) -> dict | None:
    """Verify credentials. Returns user dict on success, None on failure."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username.strip(),)
        ).fetchone()
        if row is None:
            return None

        salt = bytes.fromhex(row["salt"])
        if _hash_password(password, salt) == row["password_hash"]:
            return {"id": row["id"], "username": row["username"]}
        return None
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> dict | None:
    """Fetch a user by ID."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT id, username FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
