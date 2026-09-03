import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.db_connection import DATABASE


def main():

    with sqlite3.connect(DATABASE) as connection:
        connection.executescript((ROOT / "database" / "trust_schema.sql").read_text())
        for table, columns in {
            "users": {
                "email_verified_at": "TIMESTAMP",
                "email_verification_token_hash": "TEXT",
                "email_verification_expires_at": "TIMESTAMP",
            },
            "donors": {
                "identity_status": "TEXT DEFAULT 'Pending'",
                "identity_reference": "TEXT",
                "blood_type_verified_at": "TIMESTAMP",
                "last_donation_at": "TIMESTAMP",
            },
            "blood_requests": {
                "hospital_verified_at": "TIMESTAMP",
                "hospital_verifier_id": "INTEGER",
                "consent_version": "TEXT NOT NULL DEFAULT 'v1'",
            },
            "matches": {"outcome": "INTEGER"},
        }.items():
            existing = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
            for column, definition in columns.items():
                if column not in existing:
                    connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    print("Trust and safety schema migration complete.")


if __name__ == "__main__":
    main()
