import os
from flask import Flask

from utils.security import csrf_token, validate_csrf

from routes.auth_routes import auth_bp
from routes.dashboard_routes import dashboard_bp
from routes.profile_routes import profile_bp
from routes.donor_routes import donor_bp
from routes.request_routes import request_bp
from routes.match_routes import match_bp
from routes.admin_routes import admin_bp
from flask import render_template

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",
)

app.context_processor(lambda: {"csrf_token": csrf_token})
app.before_request(validate_csrf)

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(donor_bp)
app.register_blueprint(request_bp)
app.register_blueprint(match_bp)
app.register_blueprint(admin_bp)


@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)


    