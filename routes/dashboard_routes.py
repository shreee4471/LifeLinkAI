from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for
)

from models.donor_model import Donor


dashboard_bp = Blueprint(
    "dashboard",
    __name__
)


@dashboard_bp.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    donor = Donor.get_donor_by_user_id(
        session["user_id"]
    )

    return render_template(
        "dashboard.html",
        username=session["username"],
        email=session["email"],
        donor=donor
    )
