from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for
)

from models.user_model import User

profile_bp = Blueprint(
    "profile",
    __name__
)


@profile_bp.route("/profile")
def profile():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user = User.get_user_by_id(
        session["user_id"]
    )

    return render_template(
        "profile.html",
        user=user
    )