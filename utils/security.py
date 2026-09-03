import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque
from functools import wraps

from flask import abort, request, session


_RATE_BUCKETS = defaultdict(deque)


def csrf_token():
    token = session.get("csrf_token")
    if token is None:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def validate_csrf():
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return
    expected = session.get("csrf_token")
    supplied = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    if not expected or not supplied or not hmac.compare_digest(expected, supplied):
        abort(400, description="Invalid CSRF token")


def rate_limit(limit, window_seconds, key_prefix):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            identity = request.remote_addr or "unknown"
            if key_prefix == "auth":
                identity = f"{identity}:{request.form.get('email', '').lower()}"
            key = f"{key_prefix}:{identity}"
            now = time.monotonic()
            bucket = _RATE_BUCKETS[key]
            while bucket and now - bucket[0] >= window_seconds:
                bucket.popleft()
            if len(bucket) >= limit:
                abort(429, description="Too many requests; try again later")
            bucket.append(now)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def audit_hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
