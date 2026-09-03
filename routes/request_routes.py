from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    session,
    url_for,
    flash
)

from models.blood_request_model import BloodRequest
from models.trust_model import Trust
from services.audit_service import record_event
from utils.security import audit_hash, rate_limit


request_bp = Blueprint(
    "request",
    __name__
)


BLOOD_GROUPS = [
    "A+",
    "A-",
    "B+",
    "B-",
    "AB+",
    "AB-",
    "O+",
    "O-"
]

URGENCY_LEVELS = [
    "Critical",
    "High",
    "Medium",
    "Low"
]


def _require_login():

    if "user_id" not in session:

        flash(
            "Please login first.",
            "danger"
        )

        return redirect(
            url_for("auth.login")
        )

    return None


@request_bp.route("/requests")
def list_requests():

    login_redirect = _require_login()

    if login_redirect:
        return login_redirect

    requests = BloodRequest.get_open_requests()

    return render_template(
        "requests.html",
        requests=requests
    )


@request_bp.route("/requests/create", methods=["GET", "POST"])
@rate_limit(10, 3600, "request-create")
def create_request():

    login_redirect = _require_login()

    if login_redirect:
        return login_redirect

    if request.method == "POST":

        blood_group_needed = request.form.get("blood_group_needed", "").strip()
        city = request.form.get("city", "").strip()
        hospital_name = request.form.get("hospital_name", "").strip()
        units_required = request.form.get("units_required", "").strip()
        urgency = request.form.get("urgency", "").strip()

        if not all([
            blood_group_needed,
            city,
            hospital_name,
            units_required,
            urgency
        ]) or blood_group_needed not in BLOOD_GROUPS or urgency not in URGENCY_LEVELS:
            flash(
                "Use a valid blood group, urgency, and complete all fields.",
                "danger"
            )
            return redirect(url_for("request.create_request"))

        try:
            units_required = int(units_required)
        except ValueError:
            units_required = 0

        if units_required < 1 or units_required > 100:

            flash(
                "Units must be a whole number between 1 and 100.",
                "danger"
            )

            return redirect(
                url_for("request.create_request")
            )

        request_id = BloodRequest.create_request(
            session["user_id"],
            blood_group_needed,
            city,
            hospital_name,
            units_required,
            urgency
        )
        Trust.grant_consent(
            session["user_id"],
            "donor_contact_disclosure",
            "v1",
            audit_hash(request.remote_addr or "unknown")
        )
        record_event("request.created", "blood_request", request_id)

        flash(
            "Blood request created successfully.",
            "success"
        )

        return redirect(
            url_for(
                "request.request_details",
                request_id=request_id
            )
        )

    return render_template(
        "request_form.html",
        blood_groups=BLOOD_GROUPS,
        urgency_levels=URGENCY_LEVELS
    )


@request_bp.route("/requests/<int:request_id>")
def request_details(request_id):

    login_redirect = _require_login()

    if login_redirect:
        return login_redirect

    blood_request = BloodRequest.get_request_by_id(
        request_id
    )

    if blood_request is None:

        flash(
            "Blood request not found.",
            "warning"
        )

        return redirect(
            url_for("request.list_requests")
        )

    return render_template(
        "request_details.html",
        blood_request=blood_request
    )


@request_bp.route("/requests/<int:request_id>/close", methods=["POST"])
def close_request(request_id):

    login_redirect = _require_login()

    if login_redirect:
        return login_redirect

    closed = BloodRequest.close_request(
        request_id,
        session["user_id"]
    )

    if closed:
        flash(
            "Blood request closed successfully.",
            "success"
        )
    else:
        flash(
            "Only the requester can close an open request.",
            "danger"
        )

    return redirect(
        url_for(
            "request.request_details",
            request_id=request_id
        )
    )


@request_bp.route("/requests/history")
def request_history():

    login_redirect = _require_login()

    if login_redirect:
        return login_redirect

    requests = BloodRequest.get_requests_by_user_id(
        session["user_id"]
    )

    return render_template(
        "request_history.html",
        requests=requests
    )
