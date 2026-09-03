import os
import socket
import sys
import threading
import time
import webbrowser

from app import app


def _pick_port(preferred):
    """Return the preferred port if free, else an OS-assigned free port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]


def _wait_for_port(host, port, timeout=30):
    """Block until the server accepts TCP connections on host:port."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def _open_browser_when_ready(url, host, port):
    def _worker():
        if _wait_for_port(host, port):
            webbrowser.open(url)

    threading.Thread(target=_worker, daemon=True).start()


if __name__ == "__main__":
    from database.bootstrap import ensure_schema

    ensure_schema()

    from waitress import serve

    preferred_port = int(os.environ.get("PORT", "5000"))
    port = _pick_port(preferred_port)
    if port != preferred_port:
        print(f"Port {preferred_port} is busy; using {port} instead.")

    host = os.environ.get("HOST", "127.0.0.1")
    url = f"http://127.0.0.1:{port}/"

    if getattr(sys, "frozen", False):
        print(f"LifeLink AI is running at {url}")
        print("Keep this window open while using the app. Close it to stop.")
        _open_browser_when_ready(url, "127.0.0.1", port)

    serve(app, host=host, port=port)
