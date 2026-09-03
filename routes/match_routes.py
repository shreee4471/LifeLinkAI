from flask import (
    Blueprint,
    render_template,
    redirect,
    session,
    url_for,
    flash,
    request,
    abort
)

from models.blood_request_model import BloodRequest
from models.donor_model import Donor
from models.match_model import Match
from models.trust_model import Trust
from services.audit_service import record_event
from services.matching_service import (
    MIN_LABELED_OUTCOMES,
    rank_donors_for_request,
    retrain_model,
)
from utils.security import rate_limit


match_bp = Blueprint(
    "match",
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


def _get_owned_request(request_id):

    blood_request = BloodRequest.get_request_by_id(
        request_id
    )

    if blood_request is None:
        return None

    if blood_request["requester_id"] != session.get("user_id"):
        return None

    return blood_request


@match_bp.route("/requests/<int:request_id>/matches")
def request_matches(request_id):

    login_redirect = _require_login()

    if login_redirect:
        return login_redirect

    blood_request = _get_owned_request(
        request_id
    )

    if blood_request is None:

        flash(
            "Only the requester can view matches for this request.",
            "danger"
        )

        return redirect(
            url_for("request.list_requests")
        )

    matches = Match.get_matches_for_request(
        request_id
    )

    return render_template(
        "matches.html",
        blood_request=blood_request,
        matches=matches
    )


@match_bp.route("/requests/<int:request_id>/matches/generate", methods=["POST"])
@rate_limit(20, 3600, "match-generate")
def generate_matches(request_id):

    login_redirect = _require_login()

    if login_redirect:
        return login_redirect

    blood_request = _get_owned_request(
        request_id
    )

    if blood_request is None:

        flash(
            "Only the requester can generate matches for this request.",
            "danger"
        )

        return redirect(
            url_for("request.list_requests")
        )

    if blood_request["status"] != "Open":

        flash(
            "Matches are only generated for open requests.",
            "warning"
        )

        return redirect(
            url_for(
                "request.request_details",
                request_id=request_id
            )
        )

    if not Trust.has_consent(session["user_id"], "donor_contact_disclosure"):
        flash("Consent is required before donor contact details can be disclosed.", "warning")
        return redirect(url_for("request.request_details", request_id=request_id))

    donors = Donor.get_available_donors()
    ranked_matches = rank_donors_for_request(
        blood_request,
        donors
    )

    Match.clear_matches_for_request(
        request_id
    )

    for ranked_match in ranked_matches:
        Match.create_match(
            request_id,
            ranked_match["donor"]["id"],
            ranked_match["score"],
            ranked_match["explanation"],
            features=ranked_match["features"],
            model_version=ranked_match["model_version"]
        )

    record_event("matches.generated", "blood_request", request_id)

    flash(
        f"Generated {len(ranked_matches)} donor match(es).",
        "success"
    )

    return redirect(
        url_for(
            "match.request_matches",
            request_id=request_id
        )
    )


@match_bp.route("/matches/<int:match_id>/outcome", methods=["POST"])
def record_match_outcome(match_id):

    login_redirect = _require_login()

    if login_redirect:
        return login_redirect

    outcome = request.form.get("outcome", "")

    if outcome not in ("0", "1"):
        abort(400, description="Invalid outcome")

    match = Match.get_match_by_id(match_id)

    if match is None:
        abort(404)

    blood_request = _get_owned_request(match["request_id"])

    if blood_request is None:
        flash("Only the requester can label match outcomes.", "danger")
        return redirect(url_for("request.request_history"))

    if Match.record_outcome(match_id, int(outcome)):
        record_event("match.outcome_recorded", "match", match_id)
        flash("Outcome recorded. This helps the ranking model learn.", "success")
    else:
        flash("This match already has a recorded outcome.", "info")

    return redirect(
        url_for(
            "match.request_matches",
            request_id=match["request_id"]
        )
    )


@match_bp.route("/model/retrain", methods=["POST"])
def retrain():

    _require_login()

    if session.get("role") not in {"admin", "hospital_reviewer"}:
        abort(403)

    weights, version, labeled_count = retrain_model()
    record_event("model.retrained", "model", 1, result=f"{version}:{labeled_count}")

    if labeled_count < MIN_LABELED_OUTCOMES:
        flash(
            f"Only {labeled_count} labeled outcome(s) available; "
            f"{MIN_LABELED_OUTCOMES} are needed before training, so the prior is still in use.",
            "info"
        )
    else:
        flash(
            f"Model retrained on {labeled_count} labeled outcome(s) ({version}).",
            "success"
        )

    return redirect(url_for("admin.admin_dashboard"))
