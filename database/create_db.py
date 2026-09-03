import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.db_connection import get_db_connection


def main():

    # Connect to database
    conn = get_db_connection()

    # Create cursor
    cursor = conn.cursor()

    # ====================================
    # USERS TABLE
    # ====================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        last_login TIMESTAMP,
        email_verified_at TIMESTAMP,
        email_verification_token_hash TEXT,
        email_verification_expires_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ====================================
    # DONORS TABLE
    # ====================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS donors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        full_name TEXT NOT NULL,
        blood_group TEXT NOT NULL,
        city TEXT NOT NULL,
        phone TEXT NOT NULL,
        age INTEGER NOT NULL,
        availability TEXT DEFAULT 'Unavailable',
        identity_status TEXT DEFAULT 'Pending',
        identity_reference TEXT,
        blood_type_verified_at TIMESTAMP,
        last_donation_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (user_id)
        REFERENCES users(id)
    )
    """)

    # ====================================
    # BLOOD REQUESTS TABLE
    # ====================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS blood_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        requester_id INTEGER NOT NULL,
        blood_group_needed TEXT NOT NULL,
        city TEXT NOT NULL,
        hospital_name TEXT NOT NULL,
        units_required INTEGER NOT NULL,
        urgency TEXT NOT NULL,
        status TEXT DEFAULT 'PendingHospitalReview',
        hospital_verified_at TIMESTAMP,
        hospital_verifier_id INTEGER,
        consent_version TEXT NOT NULL DEFAULT 'v1',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (requester_id)
        REFERENCES users(id)
    )
    """)

    # ====================================
    # MATCHES TABLE
    # ====================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id INTEGER NOT NULL,
        donor_id INTEGER NOT NULL,
        match_score REAL,
        explanation TEXT,
        features TEXT,
        model_version TEXT DEFAULT 'logistic-prior-v1',
        outcome INTEGER,
        outcome_recorded_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (request_id)
        REFERENCES blood_requests(id),

        FOREIGN KEY (donor_id)
        REFERENCES donors(id)
    )
    """)

    # ====================================
    # MODEL STATE TABLE
    # ====================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS model_state (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        weights TEXT NOT NULL,
        version TEXT NOT NULL,
        labeled_outcomes INTEGER NOT NULL,
        trained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    with open(
        Path(__file__).resolve().parent / "trust_schema.sql",
        encoding="utf-8"
    ) as schema_file:
        cursor.executescript(schema_file.read())

    # Save changes
    conn.commit()

    # Close connection
    conn.close()

    print("LifeLink AI Database Created Successfully!")


if __name__ == "__main__":
    main()
