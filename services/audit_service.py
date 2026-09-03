from flask import request, session

from utils.db_connection import get_db_connection
from utils.security import audit_hash


def record_event(action, target_type=None, target_id=None, result="success"):
    connection = get_db_connection()
    connection.execute(
        """INSERT INTO audit_logs
        (actor_user_id, action, target_type, target_id, result, request_id, ip_hash, user_agent)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            session.get("user_id"),
            action,
            target_type,
            target_id,
            result,
            request.headers.get("X-Request-ID"),
            audit_hash(request.remote_addr or "unknown"),
            request.user_agent.string[:255],
        ),
    )
    connection.commit()
    connection.close()
