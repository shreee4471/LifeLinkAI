from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    session,
    url_for,
    flash
)

from models.donor_model import Donor
from models.trust_model import Trust
from services.audit_service import record_event
from services.matching_service import days_since_last_donation
from utils.security import audit_hash


donor_bp = Blueprint(
    "donor",
    __name__
)


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


@donor_bp.route("/become_donor", methods=["GET", "POST"])
def become_donor():

    login_redirect = _require_login()

    if login_redirect:
        return login_redirect

    donor = Donor.get_donor_by_user_id(
        session["user_id"]
    )

    if donor:
        flash(
            "You already have a donor profile.",
            "info"
        )

        return redirect(
            url_for("donor.donor_dashboard")
        )

    if request.method == "POST":

        full_name = request.form.get("full_name", "").strip()
        blood_group = request.form.get("blood_group", "").strip()
        city = request.form.get("city", "").strip()
        phone = request.form.get("phone", "").strip()
        age = request.form.get("age", "").strip()

        try:
            age = int(age)
        except ValueError:
            age = 0

        if not all([full_name, blood_group, city, phone]) or blood_group not in ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"] or not 18 <= age <= 65:
            flash("Enter complete donor details with a valid blood group and age (18–65).", "danger")
            return redirect(url_for("donor.become_donor"))

        Donor.create_donor(
            session["user_id"],
            full_name,
            blood_group,
            city,
            phone,
            age
        )
        donor = Donor.get_donor_by_user_id(session["user_id"])
        Trust.grant_consent(
            session["user_id"],
            "donor_availability",
            "v1",
            audit_hash(request.remote_addr or "unknown")
        )
        Trust.grant_consent(
            session["user_id"],
            "model_training_outcomes",
            "v1",
            audit_hash(request.remote_addr or "unknown")
        )
        record_event("donor.created", "donor", donor["id"])

        flash(
            "Donor profile created successfully!",
            "success"
        )

        return redirect(
            url_for("donor.donor_dashboard")
        )

    return render_template(
        "donor_profile.html",
        donor=None,
        form_title="Become a Blood Donor",
        action_label="Register as Donor"
    )


@donor_bp.route("/donor/dashboard")
def donor_dashboard():

    login_redirect = _require_login()

    if login_redirect:
        return login_redirect

    donor = Donor.get_donor_by_user_id(
        session["user_id"]
    )

    if donor is None:

        flash(
            "Create your donor profile first.",
            "warning"
        )

        return redirect(
            url_for("donor.become_donor")
        )

    donor = dict(donor)
    donor["days_since_donation"] = days_since_last_donation(donor)

    return render_template(
        "donor_dashboard.html",
        donor=donor
    )


@donor_bp.route("/donor/edit", methods=["GET", "POST"])
def edit_donor():

    login_redirect = _require_login()

    if login_redirect:
        return login_redirect

    donor = Donor.get_donor_by_user_id(
        session["user_id"]
    )

    if donor is None:

        flash(
            "Create your donor profile first.",
            "warning"
        )

        return redirect(
            url_for("donor.become_donor")
        )

    if request.method == "POST":

        full_name = request.form.get("full_name", "").strip()
        blood_group = request.form.get("blood_group", "").strip()
        city = request.form.get("city", "").strip()
        phone = request.form.get("phone", "").strip()
        age = request.form.get("age", "").strip()

        try:
            age = int(age)
        except ValueError:
            age = 0

        valid_groups = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
        if not all([full_name, blood_group, city, phone]) or blood_group not in valid_groups or not 18 <= age <= 65:
            flash("Enter complete donor details with a valid blood group and age (18–65).", "danger")
            return redirect(url_for("donor.edit_donor"))

        Donor.update_donor(
            session["user_id"],
            full_name,
            blood_group,
            city,
            phone,
            age
        )

        flash(
            "Donor profile updated successfully.",
            "success"
        )

        return redirect(
            url_for("donor.donor_dashboard")
        )

    return render_template(
        "donor_profile.html",
        donor=donor,
        form_title="Edit Donor Profile",
        action_label="Save Changes"
    )


@donor_bp.route("/donor/availability/toggle", methods=["POST"])
def toggle_availability():

    login_redirect = _require_login()

    if login_redirect:
        return login_redirect

    donor = Donor.get_donor_by_user_id(
        session["user_id"]
    )

    if donor is None:

        flash(
            "Create your donor profile first.",
            "warning"
        )

        return redirect(
            url_for("donor.become_donor")
        )

    new_availability = (
        "Unavailable"
        if donor["availability"] == "Available"
        else "Available"
    )

    Donor.update_availability(
        session["user_id"],
        new_availability
    )

    flash(
        f"Availability changed to {new_availability}.",
        "success"
    )

    return redirect(
        url_for("donor.donor_dashboard")
    )


@donor_bp.route("/donor/donations/log", methods=["POST"])
def log_donation():

    login_redirect = _require_login()

    if login_redirect:
        return login_redirect

    donor = Donor.get_donor_by_user_id(
        session["user_id"]
    )

    if donor is None:

        flash(
            "Create your donor profile first.",
            "warning"
        )

        return redirect(
            url_for("donor.become_donor")
        )

    if Donor.record_donation(donor["id"]):
        Donor.update_availability(session["user_id"], "Unavailable")
        record_event("donation.logged", "donor", donor["id"])
        flash(
            "Donation recorded. You are marked unavailable for the 56-day whole-blood cooldown.",
            "success"
        )
    else:
        flash("Could not record the donation.", "danger")

    return redirect(
        url_for("donor.donor_dashboard")
    )
