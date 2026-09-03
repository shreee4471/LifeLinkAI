import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.db_connection import DATABASE


def main():

    with sqlite3.connect(DATABASE) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(matches)")
        }
        if "explanation" not in columns:
            connection.execute("ALTER TABLE matches ADD COLUMN explanation TEXT")
        if "model_version" not in columns:
            connection.execute(
                "ALTER TABLE matches ADD COLUMN model_version TEXT DEFAULT 'logistic-prior-v1'"
            )
        if "outcome" not in columns:
            connection.execute("ALTER TABLE matches ADD COLUMN outcome INTEGER")
        if "outcome_recorded_at" not in columns:
            connection.execute("ALTER TABLE matches ADD COLUMN outcome_recorded_at TIMESTAMP")
        if "features" not in columns:
            connection.execute("ALTER TABLE matches ADD COLUMN features TEXT")

        connection.execute("""
            CREATE TABLE IF NOT EXISTS model_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                weights TEXT NOT NULL,
                version TEXT NOT NULL,
                labeled_outcomes INTEGER NOT NULL,
                trained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    print("Match metadata migration complete.")


if __name__ == "__main__":
    main()
