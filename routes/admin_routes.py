from flask import (
    Blueprint,
    abort,
    redirect,
    render_template,
    request,
    session,
    url_for,
    flash
)

from models.blood_request_model import BloodRequest
from models.donor_model import Donor
from models.match_model import Match
from models.trust_model import Trust
from models.user_model import User
from services.audit_service import record_event
from utils.security import rate_limit


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


VALID_ROLES = {"user", "hospital_reviewer", "admin"}


def _require_role(*roles):
    if session.get("role") not in roles:
        abort(403)


@admin_bp.route("")
def admin_dashboard():

    _require_role("admin", "hospital_reviewer")

    pending_donors = Donor.get_pending_donors()
    pending_requests = BloodRequest.get_pending_review_requests()
    model_state = Match.get_model_state()
    labeled_count = sum(
        1 for row in Match.get_labeled_outcomes() if row["outcome"] in (0, 1)
    )
    users = User.get_users_with_roles() if session.get("role") == "admin" else []

    return render_template(
        "admin_dashboard.html",
        pending_donors=pending_donors,
        pending_requests=pending_requests,
        model_state=model_state,
        labeled_count=labeled_count,
        users=users,
        is_admin=session.get("role") == "admin",
    )


@admin_bp.post("/donors/<int:donor_id>/verify")
def verify_donor(donor_id):

    _require_role("admin", "hospital_reviewer")

    decision = request.form.get("decision", "")

    if decision not in ("approve", "reject"):
        abort(400, description="Invalid decision")

    if decision == "approve":
        Trust.set_donor_verification(
            donor_id,
            "Verified",
            "Verified",
            session["user_id"],
        )
        record_event("donor.verified", "donor", donor_id)
        flash("Donor identity and blood group verified.", "success")
    else:
        Trust.set_donor_verification(
            donor_id,
            "Rejected",
            "Rejected",
            session["user_id"],
            reason="Reviewer rejected the verification",
        )
        record_event("donor.rejected", "donor", donor_id, result="rejected")
        flash("Donor verification rejected.", "warning")

    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.post("/requests/<int:request_id>/verify")
def verify_request(request_id):

    _require_role("admin", "hospital_reviewer")

    if Trust.verify_hospital_request(request_id, session["user_id"]):
        record_event("hospital_request.verified", "blood_request", request_id)
        flash("Request verified and opened for matching.", "success")
    else:
        flash("Only requests pending hospital review can be verified.", "warning")

    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.post("/users/<int:user_id>/role")
@rate_limit(20, 3600, "role-change")
def change_user_role(user_id):

    _require_role("admin")

    role = request.form.get("role", "")

    if role not in VALID_ROLES:
        abort(400, description="Invalid role")

    if user_id == session["user_id"] and role != "admin":
        flash("Admins cannot demote themselves.", "danger")
        return redirect(url_for("admin.admin_dashboard"))

    if User.set_role(user_id, role):
        record_event("user.role_changed", "user", user_id, result=role)
        flash(f"Role updated to {role}.", "success")
    else:
        flash("User not found.", "danger")

    return redirect(url_for("admin.admin_dashboard"))
