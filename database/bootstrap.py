"""Idempotent schema bootstrap: create tables if missing, then apply migrations."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.create_db import main as create_schema
from database.migrate_matches import main as migrate_matches
from database.migrate_trust import main as migrate_trust


def ensure_schema():
    create_schema()
    migrate_matches()
    migrate_trust()


if __name__ == "__main__":
    ensure_schema()
    print("Database schema is up to date.")
