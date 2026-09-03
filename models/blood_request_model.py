from utils.db_connection import get_db_connection


class BloodRequest:

    @staticmethod
    def create_request(
        requester_id,
        blood_group_needed,
        city,
        hospital_name,
        units_required,
        urgency
    ):

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO blood_requests (
                requester_id,
                blood_group_needed,
                city,
                hospital_name,
                units_required,
                urgency
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            requester_id,
            blood_group_needed,
            city,
            hospital_name,
            units_required,
            urgency
        ))

        conn.commit()
        request_id = cursor.lastrowid
        conn.close()

        return request_id

    @staticmethod
    def get_open_requests():

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                blood_requests.*,
                users.username AS requester_name
            FROM blood_requests
            JOIN users
                ON users.id = blood_requests.requester_id
            WHERE blood_requests.status = 'Open'
            ORDER BY
                CASE blood_requests.urgency
                    WHEN 'Critical' THEN 1
                    WHEN 'High' THEN 2
                    WHEN 'Medium' THEN 3
                    ELSE 4
                END,
                blood_requests.created_at DESC
        """)

        requests = cursor.fetchall()

        conn.close()

        return requests

    @staticmethod
    def get_request_by_id(request_id):

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                blood_requests.*,
                users.username AS requester_name,
                users.email AS requester_email
            FROM blood_requests
            JOIN users
                ON users.id = blood_requests.requester_id
            WHERE blood_requests.id = ?
        """, (request_id,))

        blood_request = cursor.fetchone()

        conn.close()

        return blood_request

    @staticmethod
    def get_requests_by_user_id(user_id):

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM blood_requests
            WHERE requester_id = ?
            ORDER BY created_at DESC
        """, (user_id,))

        requests = cursor.fetchall()

        conn.close()

        return requests

    @staticmethod
    def get_pending_review_requests():

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                blood_requests.*,
                users.username AS requester_name
            FROM blood_requests
            JOIN users
                ON users.id = blood_requests.requester_id
            WHERE blood_requests.status = 'PendingHospitalReview'
            ORDER BY blood_requests.created_at ASC
        """)

        requests = cursor.fetchall()

        conn.close()

        return requests

    @staticmethod
    def close_request(request_id, requester_id):

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE blood_requests
            SET status = 'Closed'
            WHERE id = ?
                AND requester_id = ?
                AND status = 'Open'
        """, (
            request_id,
            requester_id
        ))

        updated_count = cursor.rowcount

        conn.commit()
        conn.close()

        return updated_count > 0
