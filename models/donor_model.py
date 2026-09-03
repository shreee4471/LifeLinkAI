from utils.db_connection import get_db_connection


class Donor:

    @staticmethod
    def create_donor(
        user_id,
        full_name,
        blood_group,
        city,
        phone,
        age
    ):

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO donors (
                user_id,
                full_name,
                blood_group,
                city,
                phone,
                age
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            full_name,
            blood_group,
            city,
            phone,
            age
        ))

        conn.commit()
        conn.close()

    @staticmethod
    def get_donor_by_user_id(user_id):

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM donors
            WHERE user_id = ?
        """, (user_id,))

        donor = cursor.fetchone()

        conn.close()

        return donor

    @staticmethod
    def get_available_donors():

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM donors
            WHERE availability = 'Available'
                AND identity_status = 'Verified'
                AND blood_type_verified_at IS NOT NULL
            ORDER BY city ASC,
                blood_group ASC,
                full_name ASC
        """)

        donors = cursor.fetchall()

        conn.close()

        return donors

    @staticmethod
    def update_donor(
        user_id,
        full_name,
        blood_group,
        city,
        phone,
        age
    ):

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE donors
            SET
                full_name = ?,
                blood_group = ?,
                city = ?,
                phone = ?,
                age = ?
            WHERE user_id = ?
        """, (
            full_name,
            blood_group,
            city,
            phone,
            age,
            user_id
        ))

        conn.commit()
        conn.close()

    @staticmethod
    def update_availability(user_id, availability):

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE donors
            SET availability = ?
            WHERE user_id = ?
        """, (
            availability,
            user_id
        ))

        conn.commit()
        conn.close()

    @staticmethod
    def record_donation(donor_id):

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE donors
            SET last_donation_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (donor_id,))

        updated_count = cursor.rowcount

        conn.commit()
        conn.close()

        return updated_count > 0

    @staticmethod
    def get_pending_donors():

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM donors
            WHERE identity_status = 'Pending'
            ORDER BY created_at ASC
        """)

        donors = cursor.fetchall()

        conn.close()

        return donors
