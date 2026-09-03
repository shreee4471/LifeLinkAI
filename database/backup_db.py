import argparse
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.db_connection import DATABASE


parser = argparse.ArgumentParser(description="Create a consistent SQLite backup.")
parser.add_argument("destination", nargs="?", default=None)
args = parser.parse_args()

stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
destination = Path(args.destination or f"database/backups/lifelink-{stamp}.db")
destination.parent.mkdir(parents=True, exist_ok=True)

with sqlite3.connect(DATABASE) as source, sqlite3.connect(destination) as target:
    source.backup(target)

print(f"Backup created: {destination}")
