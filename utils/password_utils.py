from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash


def hash_password(password):
    """
    Convert plain text password into a secure hash.
    """
    return generate_password_hash(password)


def verify_password(stored_hash, password):
    """
    Verify entered password against stored hash.
    """
    return check_password_hash(stored_hash, password)