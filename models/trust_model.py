from utils.db_connection import get_db_connection


class Trust:
    @staticmethod
    def grant_consent(user_id, purpose, policy_version, ip_hash):
        connection = get_db_connection()
        connection.execute(
            "INSERT INTO consent_records (user_id, purpose, policy_version, capture_ip_hash) VALUES (?, ?, ?, ?)",
            (user_id, purpose, policy_version, ip_hash),
        )
        connection.commit()
        connection.close()

    @staticmethod
    def has_consent(user_id, purpose):
        connection = get_db_connection()
        row = connection.execute(
            "SELECT 1 FROM consent_records WHERE user_id = ? AND purpose = ? AND revoked_at IS NULL ORDER BY granted_at DESC LIMIT 1",
            (user_id, purpose),
        ).fetchone()
        connection.close()
        return row is not None

    @staticmethod
    def set_donor_verification(donor_id, identity_status, blood_type_status, reviewer_id, reason=None):
        connection = get_db_connection()
        connection.execute(
            """INSERT INTO donor_verifications
            (donor_id, identity_status, blood_type_status, reviewer_user_id, reviewed_at, rejection_reason)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)""",
            (donor_id, identity_status, blood_type_status, reviewer_id, reason),
        )
        connection.execute(
            "UPDATE donors SET identity_status = ?, blood_type_verified_at = CASE WHEN ? = 'Verified' THEN CURRENT_TIMESTAMP ELSE NULL END WHERE id = ?",
            (identity_status, blood_type_status, donor_id),
        )
        connection.commit()
        connection.close()

    @staticmethod
    def verify_hospital_request(request_id, verifier_id):
        connection = get_db_connection()
        connection.execute(
            "UPDATE blood_requests SET status = 'Open', hospital_verified_at = CURRENT_TIMESTAMP, hospital_verifier_id = ? WHERE id = ? AND status = 'PendingHospitalReview'",
            (verifier_id, request_id),
        )
        changed = connection.total_changes
        connection.commit()
        connection.close()
        return changed > 0
