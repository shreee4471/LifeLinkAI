import json

from utils.db_connection import get_db_connection


class Match:

    @staticmethod
    def clear_matches_for_request(request_id):

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM matches
            WHERE request_id = ?
        """, (request_id,))

        conn.commit()
        conn.close()

    @staticmethod
    def create_match(request_id, donor_id, match_score, explanation, features=None, model_version=None):

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO matches (
                request_id,
                donor_id,
                match_score,
                explanation,
                features,
                model_version
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            request_id,
            donor_id,
            match_score,
            explanation,
            json.dumps(features) if features else None,
            model_version,
        ))

        conn.commit()
        conn.close()

    @staticmethod
    def get_matches_for_request(request_id):

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                matches.*,
                donors.full_name,
                donors.blood_group,
                donors.city,
                donors.phone,
                donors.age,
                donors.availability,
                matches.explanation,
                matches.model_version
            FROM matches
            JOIN donors
                ON donors.id = matches.donor_id
            WHERE matches.request_id = ?
            ORDER BY matches.match_score DESC,
                matches.created_at DESC
        """, (request_id,))

        matches = cursor.fetchall()

        conn.close()

        return matches

    @staticmethod
    def get_match_by_id(match_id):

        conn = get_db_connection()

        match = conn.execute("""
            SELECT *
            FROM matches
            WHERE id = ?
        """, (match_id,)).fetchone()

        conn.close()

        return match

    @staticmethod
    def record_outcome(match_id, outcome):

        conn = get_db_connection()

        cursor = conn.execute("""
            UPDATE matches
            SET outcome = ?,
                outcome_recorded_at = CURRENT_TIMESTAMP
            WHERE id = ?
                AND outcome IS NULL
        """, (outcome, match_id))

        changed = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return changed

    @staticmethod
    def get_labeled_outcomes():

        conn = get_db_connection()

        rows = conn.execute("""
            SELECT outcome, features
            FROM matches
            WHERE outcome IN (0, 1)
                AND features IS NOT NULL
        """).fetchall()

        conn.close()

        labeled = []
        for row in rows:
            try:
                features = json.loads(row["features"])
            except (ValueError, TypeError):
                continue
            labeled.append({"features": features, "outcome": row["outcome"]})

        return labeled

    @staticmethod
    def get_model_state():

        conn = get_db_connection()

        state = conn.execute("""
            SELECT weights, version, labeled_outcomes, trained_at
            FROM model_state
            WHERE id = 1
        """).fetchone()

        conn.close()

        return state

    @staticmethod
    def save_model_state(weights, version, labeled_outcomes):

        conn = get_db_connection()

        conn.execute("""
            INSERT INTO model_state (id, weights, version, labeled_outcomes, trained_at)
            VALUES (1, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                weights = excluded.weights,
                version = excluded.version,
                labeled_outcomes = excluded.labeled_outcomes,
                trained_at = CURRENT_TIMESTAMP
        """, (
            json.dumps(weights),
            version,
            labeled_outcomes,
        ))

        conn.commit()
        conn.close()
