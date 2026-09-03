from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
import hashlib
import os
import secrets
import smtplib

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

from models.user_model import User

from utils.password_utils import (
    hash_password,
    verify_password
)
from utils.security import rate_limit

auth_bp = Blueprint(
    "auth",
    __name__
)


def _send_verification_email(email, token):
    host = os.environ.get("SMTP_HOST")
    username = os.environ.get("SMTP_USERNAME")
    password = os.environ.get("SMTP_PASSWORD")
    if not all([host, username, password]):
        return False
    message = EmailMessage()
    message["Subject"] = "Verify your LifeLink account"
    message["From"] = os.environ.get("SMTP_FROM", username)
    message["To"] = email
    base_url = os.environ.get("PUBLIC_BASE_URL", "http://127.0.0.1:5000")
    message.set_content(f"Verify your account: {base_url}/verify-email/{token}")
    with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", "587"))) as server:
        server.starttls()
        server.login(username, password)
        server.send_message(message)
    return True

# =========================
# Register routing
# =========================


@auth_bp.route("/register", methods=["GET", "POST"])
@rate_limit(5, 900, "auth")
def register():

    if request.method == "POST":

        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        # Validation
        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("auth.register"))

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("auth.register"))

        # Check username
        existing_user = User.get_user_by_username(username)

        if existing_user:
            flash("Username already exists.", "danger")
            return redirect(url_for("auth.register"))

        # Check email
        existing_email = User.get_user_by_email(email)

        if existing_email:
            flash("Email already registered.", "danger")
            return redirect(url_for("auth.register"))

        # Hash password
        password_hash = hash_password(password)

        # Save user
        User.create_user(
            username,
            email,
            password_hash
        )
        token = secrets.token_urlsafe(32)
        User.set_email_verification(
            User.get_user_by_email(email)["id"],
            hashlib.sha256(token.encode()).hexdigest(),
            # SQLite format so the CURRENT_TIMESTAMP comparison in verify_email is valid
            (datetime.now(timezone.utc) + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
        )

        if _send_verification_email(email, token):
            flash(
                "Registration successful. Check your email to verify your account before using donor or request features.",
                "success"
            )
        else:
            verification_url = url_for("auth.verify_email", token=token, _external=True)
            flash(
                "Registration successful. Email delivery is not configured on this server, "
                f"so verify your account with this link (valid 24 hours): {verification_url}",
                "success"
            )

        return redirect(url_for("auth.login"))

    return render_template("register.html")



# =========================
# Login routing
# =========================

@auth_bp.route("/verify-email/<token>")
def verify_email(token):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    if User.verify_email(token_hash):
        flash("Email verified successfully. You can now sign in.", "success")
    else:
        flash("This verification link is invalid or expired.", "danger")
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
@rate_limit(10, 900, "auth")
def login():

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        # Check if user exists
        user = User.get_user_by_email(email)

        if user is None:
            flash("Invalid Email or Password", "danger")
            return redirect(url_for("auth.login"))

        # Verify password
        if not verify_password(
            user["password_hash"],
            password
        ):
            flash("Invalid Email or Password", "danger")
            return redirect(url_for("auth.login"))

        # Update last login time
        User.update_last_login(user["id"])

        # Create session
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["email"] = user["email"]
        session["role"] = user["role"]

        flash(
            f"Welcome back, {user['username']}!",
            "success"
        )

        return redirect(
            url_for("dashboard.dashboard")
        )

    return render_template("login.html")



# =========================
# Logout routing
# =========================

@auth_bp.route("/logout", methods=["POST"])
def logout():

    session.clear()

    return redirect(url_for("auth.login"))





