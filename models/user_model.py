from utils.db_connection import get_db_connection


class User:

    @staticmethod
    def create_user(username, email, password_hash):

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO users
            (username, email, password_hash)
            VALUES (?, ?, ?)
        """, (username, email, password_hash))

        conn.commit()
        conn.close()

    @staticmethod
    def set_email_verification(user_id, token_hash, expires_at):
        conn = get_db_connection()
        conn.execute("UPDATE users SET email_verification_token_hash = ?, email_verification_expires_at = ? WHERE id = ?", (token_hash, expires_at, user_id))
        conn.commit()
        conn.close()

    @staticmethod
    def verify_email(token_hash):
        conn = get_db_connection()
        row = conn.execute("SELECT id FROM users WHERE email_verification_token_hash = ? AND email_verification_expires_at > CURRENT_TIMESTAMP", (token_hash,)).fetchone()
        if row:
            conn.execute("UPDATE users SET email_verified_at = CURRENT_TIMESTAMP, email_verification_token_hash = NULL, email_verification_expires_at = NULL WHERE id = ?", (row["id"],))
            conn.commit()
        conn.close()
        return row

    @staticmethod
    def get_user_by_email(email):

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM users
            WHERE email = ?
        """, (email,))

        user = cursor.fetchone()

        conn.close()

        return user

    @staticmethod
    def get_user_by_username(username):

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM users
            WHERE username = ?
        """, (username,))

        user = cursor.fetchone()

        conn.close()

        return user
    


    @staticmethod
    def get_user_by_id(user_id):

     conn = get_db_connection()
     cursor = conn.cursor()

     cursor.execute("""
        SELECT *
        FROM users
        WHERE id = ?
    """, (user_id,))

     user = cursor.fetchone()

     conn.close()

     return user
    

    @staticmethod
    def update_last_login(user_id):

     conn = get_db_connection()
     cursor = conn.cursor()

     cursor.execute("""
        UPDATE users
        SET last_login = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (user_id,))

     conn.commit()
     conn.close()

    @staticmethod
    def set_role(user_id, role):

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE users
            SET role = ?
            WHERE id = ?
        """, (role, user_id))

        updated_count = cursor.rowcount

        conn.commit()
        conn.close()

        return updated_count > 0

    @staticmethod
    def get_users_with_roles():

        conn = get_db_connection()

        users = conn.execute("""
            SELECT id, username, email, role, email_verified_at, created_at
            FROM users
            ORDER BY created_at ASC
        """).fetchall()

        conn.close()

        return users