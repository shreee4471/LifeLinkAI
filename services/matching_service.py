"""Medical safety constraints and explainable donor ranking.

Ranking is a two-stage pipeline:

1. A deterministic medical gate (ABO/Rh red-cell compatibility, donor age
   window, and the 56-day whole-blood donation cooldown) filters candidates.
   This stage never uses learned components.
2. Eligible candidates are scored with a logistic probability. Weights start
   from a transparent domain-informed prior and are refit from labeled match
   outcomes once enough real data exists.

Scores are ranking signals, not medical guarantees.
"""

import json
import math
import sqlite3
from datetime import datetime, timezone

from services.clinical_policy import BLOOD_COMPATIBILITY, POLICY_VERSION

MODEL_VERSION = "logistic-prior-v1"
TRAINED_MODEL_VERSION = "logistic-trained-v1"
FEATURE_NAMES = ("same_city", "available", "urgency", "age_fit", "recent_donation")
MIN_LABELED_OUTCOMES = 10
DONATION_COOLDOWN_DAYS = 56
MIN_DONOR_AGE = 18
MAX_DONOR_AGE = 65

URGENCY_WEIGHT = {"Critical": 1.0, "High": 0.75, "Medium": 0.45, "Low": 0.2}

# Prior learned from domain-informed historical response assumptions. Once
# outcomes exist in matches, logistic regression is refit from the
# application's own data and stored in model_state.
PRIOR_WEIGHTS = {
    "intercept": -1.0,
    "same_city": 1.35,
    "available": 1.1,
    "urgency": 0.55,
    "age_fit": 0.25,
    "recent_donation": -0.7,
}


def normalize_text(value):
    return str(value or "").strip().lower()


def is_blood_compatible(requested_group, donor_group):
    return donor_group in BLOOD_COMPATIBILITY.get(requested_group, [])


def _parse_timestamp(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def days_since_last_donation(donor, now=None):
    last_donation = _parse_timestamp(donor["last_donation_at"] if "last_donation_at" in donor.keys() else None)
    if last_donation is None:
        return None
    now = now or datetime.now(timezone.utc)
    return max(0, (now - last_donation).days)


def is_eligible_donor(donor, now=None):
    """Deterministic medical gate: age window and donation cooldown."""
    age = float(donor["age"] or 0)
    if not MIN_DONOR_AGE <= age <= MAX_DONOR_AGE:
        return False
    days = days_since_last_donation(donor, now)
    if days is not None and days < DONATION_COOLDOWN_DAYS:
        return False
    return True


def _features(blood_request, donor, now=None):
    age = float(donor["age"] or 0)
    age_fit = 1.0 if MIN_DONOR_AGE <= age <= MAX_DONOR_AGE else 0.0
    days = days_since_last_donation(donor, now)
    return {
        "same_city": float(normalize_text(blood_request["city"]) == normalize_text(donor["city"])),
        "available": float(donor["availability"] == "Available"),
        "urgency": URGENCY_WEIGHT.get(blood_request["urgency"], 0.0),
        "age_fit": age_fit,
        "recent_donation": float(days is not None and days < DONATION_COOLDOWN_DAYS),
    }


def _sigmoid(value):
    return 1 / (1 + math.exp(-max(-40, min(40, value))))


def _probability(features, weights):
    value = weights["intercept"]
    value += sum(
        weights[name] * feature
        for name, feature in features.items()
        if name in weights
    )
    return _sigmoid(value)


def fit_logistic_weights(rows):
    """Fit logistic weights from labeled match outcomes using gradient descent.

    rows: iterable of {"features": {name: float}, "outcome": 0|1}
    Falls back to the prior when fewer than MIN_LABELED_OUTCOMES labeled rows
    exist, mirroring load_weights_for_ranking's behavior for live ranking.
    """
    labeled = [row for row in rows if row["outcome"] in (0, 1)]
    if len(labeled) < MIN_LABELED_OUTCOMES:
        return PRIOR_WEIGHTS.copy(), MODEL_VERSION

    weights = PRIOR_WEIGHTS.copy()
    learning_rate = 0.08
    for _ in range(250):
        gradients = {name: 0.0 for name in weights}
        for row in labeled:
            features = row["features"]
            prediction = _probability(features, weights)
            error = prediction - row["outcome"]
            gradients["intercept"] += error
            for name, feature in features.items():
                if name in gradients:
                    gradients[name] += error * feature
        for name in weights:
            weights[name] -= learning_rate * gradients[name] / len(labeled)
    return weights, TRAINED_MODEL_VERSION


def load_weights_for_ranking():
    """Load trained weights from model_state, or the prior for fresh installs."""
    from models.match_model import Match

    try:
        state = Match.get_model_state()
    except sqlite3.OperationalError:
        # Legacy database without the model_state table yet
        return PRIOR_WEIGHTS.copy(), MODEL_VERSION
    if state is not None and state["weights"]:
        try:
            weights = json.loads(state["weights"])
            if "intercept" in weights and all(name in weights for name in FEATURE_NAMES):
                return weights, state["version"]
        except (ValueError, TypeError):
            pass
    return PRIOR_WEIGHTS.copy(), MODEL_VERSION


def retrain_model():
    """Refit weights from labeled match outcomes and persist to model_state."""
    from models.match_model import Match

    rows = Match.get_labeled_outcomes()
    weights, version = fit_logistic_weights(rows)
    labeled_count = sum(1 for row in rows if row["outcome"] in (0, 1))
    Match.save_model_state(weights, version, labeled_count)
    return weights, version, labeled_count


def calculate_match_score(blood_request, donor, weights=None):
    """Pure score helper: deterministic gate + logistic probability.

    Uses the prior weights by default; this function never touches the DB.
    """
    if not is_blood_compatible(blood_request["blood_group_needed"], donor["blood_group"]):
        return 0
    if not is_eligible_donor(donor):
        return 0
    if weights is None:
        weights = PRIOR_WEIGHTS
    return round(_probability(_features(blood_request, donor), weights) * 100, 2)


def rank_donors_for_request(blood_request, donors, weights=None, model_version=None):
    """Rank donors. Pass weights/model_version to run without touching the DB."""
    if weights is None:
        weights, model_version = load_weights_for_ranking()
    elif model_version is None:
        model_version = MODEL_VERSION
    ranked_matches = []
    for donor in donors:
        if not is_blood_compatible(blood_request["blood_group_needed"], donor["blood_group"]):
            continue
        if not is_eligible_donor(donor):
            continue
        features = _features(blood_request, donor)
        probability = _probability(features, weights)
        reasons = []
        if features["same_city"]:
            reasons.append("same city")
        if features["available"]:
            reasons.append("currently available")
        if features["age_fit"]:
            reasons.append("eligible donor age")
        else:
            reasons.append("outside preferred donor age")
        days = days_since_last_donation(donor)
        if days is not None and days < DONATION_COOLDOWN_DAYS:
            reasons.append(f"donated {days} days ago (within {DONATION_COOLDOWN_DAYS}-day cooldown)")
        reasons.append(f"{blood_request['urgency'].lower()} urgency priority")
        ranked_matches.append({
            "donor": donor,
            "score": round(probability * 100, 2),
            "probability": round(probability, 4),
            "explanation": "Compatible blood group; " + ", ".join(reasons) + ".",
            "features": features,
            "model_version": model_version,
        })
    return sorted(ranked_matches, key=lambda match: match["probability"], reverse=True)
