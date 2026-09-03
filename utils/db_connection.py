import os
import sys
import sqlite3
from pathlib import Path


if getattr(sys, "frozen", False):
    # Frozen (PyInstaller) build: keep writable data next to the executable.
    # The default temp extraction dir is deleted on exit and must never hold
    # the database.
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent


DATABASE = os.environ.get(
    "LIFELINK_DATABASE",
    str(BASE_DIR / "database" / "login_auth.db")
)


def get_db_connection():
    Path(DATABASE).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
