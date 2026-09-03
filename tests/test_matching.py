"""Unit tests for the deterministic medical gate and ranking model."""

from datetime import datetime, timedelta, timezone

import pytest

from services.matching_service import (
    DONATION_COOLDOWN_DAYS,
    FEATURE_NAMES,
    MIN_LABELED_OUTCOMES,
    PRIOR_WEIGHTS,
    _features,
    calculate_match_score,
    days_since_last_donation,
    fit_logistic_weights,
    is_blood_compatible,
    is_eligible_donor,
    rank_donors_for_request,
)

NOW = datetime(2026, 9, 3, 12, 0, 0, tzinfo=timezone.utc)


class FakeDonor(dict):
    """Mimics sqlite3.Row key access for columns like last_donation_at."""

    def __init__(self, **kwargs):
        defaults = {
            "id": 1,
            "full_name": "Test Donor",
            "blood_group": "O-",
            "city": "Mumbai",
            "age": 30,
            "availability": "Available",
            "last_donation_at": None,
        }
        defaults.update(kwargs)
        super().__init__(defaults)

    def keys(self):
        return super().keys()


def make_request(**kwargs):
    defaults = {
        "id": 1,
        "blood_group_needed": "O-",
        "city": "Mumbai",
        "urgency": "High",
    }
    defaults.update(kwargs)
    return defaults


class TestBloodCompatibility:
    def test_o_negative_donates_to_everyone(self):
        for recipient in ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]:
            assert is_blood_compatible(recipient, "O-")

    def test_ab_positive_receives_from_everyone(self):
        for donor in ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]:
            assert is_blood_compatible("AB+", donor)

    def test_incompatible_pairs_rejected(self):
        assert not is_blood_compatible("O-", "O+")
        assert not is_blood_compatible("A+", "B+")
        assert not is_blood_compatible("B-", "A-")
        assert not is_blood_compatible("A-", "AB-")

    def test_unknown_group_rejected(self):
        assert not is_blood_compatible("C+", "O-")
        assert not is_blood_compatible("O-", "C+")


class TestEligibilityGate:
    def test_eligible_donor_passes(self):
        donor = FakeDonor()
        assert is_eligible_donor(donor, now=NOW)

    def test_underage_donor_rejected(self):
        assert not is_eligible_donor(FakeDonor(age=17), now=NOW)

    def test_overage_donor_rejected(self):
        assert not is_eligible_donor(FakeDonor(age=66), now=NOW)

    def test_recent_donor_rejected(self):
        recent = (NOW - timedelta(days=10)).isoformat()
        assert not is_eligible_donor(FakeDonor(last_donation_at=recent), now=NOW)

    def test_donor_exactly_at_cooldown_boundary_passes(self):
        boundary = (NOW - timedelta(days=DONATION_COOLDOWN_DAYS)).isoformat()
        assert is_eligible_donor(FakeDonor(last_donation_at=boundary), now=NOW)

    def test_donor_past_cooldown_passes(self):
        old = (NOW - timedelta(days=90)).isoformat()
        assert is_eligible_donor(FakeDonor(last_donation_at=old), now=NOW)

    def test_malformed_timestamp_treated_as_no_donation(self):
        donor = FakeDonor(last_donation_at="not-a-date")
        assert days_since_last_donation(donor, now=NOW) is None
        assert is_eligible_donor(donor, now=NOW)


class TestFeatures:
    def test_feature_names_and_ranges(self):
        features = _features(make_request(), FakeDonor(), now=NOW)
        assert set(features) == set(FEATURE_NAMES)
        assert all(0.0 <= value <= 1.0 for value in features.values())

    def test_same_city_feature(self):
        features = _features(make_request(city="Mumbai"), FakeDonor(city="mumbai "), now=NOW)
        assert features["same_city"] == 1.0

    def test_different_city_feature(self):
        features = _features(make_request(city="Delhi"), FakeDonor(city="Mumbai"), now=NOW)
        assert features["same_city"] == 0.0

    def test_recent_donation_feature(self):
        recent = (NOW - timedelta(days=5)).isoformat()
        features = _features(make_request(), FakeDonor(last_donation_at=recent), now=NOW)
        assert features["recent_donation"] == 1.0


class TestRanking:
    def test_incompatible_donor_never_ranked(self):
        donors = [
            FakeDonor(id=1, blood_group="B+"),
            FakeDonor(id=2, blood_group="O-"),
        ]
        ranked = rank_donors_for_request(make_request(blood_group_needed="O-"), donors, weights=PRIOR_WEIGHTS)
        assert [match["donor"]["id"] for match in ranked] == [2]

    def test_cooldown_donor_excluded_from_ranking(self):
        recent = (NOW - timedelta(days=3)).isoformat()
        donors = [
            FakeDonor(id=1, last_donation_at=recent),
            FakeDonor(id=2),
        ]
        ranked = rank_donors_for_request(make_request(), donors, weights=PRIOR_WEIGHTS)
        assert [match["donor"]["id"] for match in ranked] == [2]

    def test_same_city_ranks_above_other_city(self):
        donors = [
            FakeDonor(id=1, city="Delhi"),
            FakeDonor(id=2, city="Mumbai"),
        ]
        ranked = rank_donors_for_request(make_request(city="Mumbai"), donors, weights=PRIOR_WEIGHTS)
        assert ranked[0]["donor"]["id"] == 2

    def test_results_sorted_descending(self):
        donors = [
            FakeDonor(id=1, city="Delhi"),
            FakeDonor(id=2, city="Mumbai"),
            FakeDonor(id=3, city="MUMBAI"),
        ]
        ranked = rank_donors_for_request(make_request(city="Mumbai"), donors, weights=PRIOR_WEIGHTS)
        scores = [match["probability"] for match in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_every_result_carries_explanation_and_features(self):
        ranked = rank_donors_for_request(make_request(), [FakeDonor()], weights=PRIOR_WEIGHTS)
        assert len(ranked) == 1
        assert "Compatible blood group" in ranked[0]["explanation"]
        assert set(ranked[0]["features"]) == set(FEATURE_NAMES)
        assert ranked[0]["model_version"]

    def test_score_matches_probability(self):
        ranked = rank_donors_for_request(make_request(), [FakeDonor()], weights=PRIOR_WEIGHTS)
        assert ranked[0]["score"] == pytest.approx(ranked[0]["probability"] * 100, abs=0.01)

    def test_calculate_match_score_zero_for_incompatible(self):
        assert calculate_match_score(make_request(), FakeDonor(blood_group="B+")) == 0


class TestTraining:
    def test_prior_returned_below_minimum_labeled(self):
        rows = [
            {"features": {"same_city": 1.0, "available": 1.0, "urgency": 0.75, "age_fit": 1.0, "recent_donation": 0.0}, "outcome": 1}
            for _ in range(MIN_LABELED_OUTCOMES - 1)
        ]
        weights, version = fit_logistic_weights(rows)
        assert weights == PRIOR_WEIGHTS
        assert version == "logistic-prior-v1"

    def test_weights_change_when_trained(self):
        rows = []
        for i in range(30):
            # Same-city, available donors always respond; far-away donors never do
            same_city = float(i % 2 == 0)
            rows.append({
                "features": {"same_city": same_city, "available": 1.0, "urgency": 0.75, "age_fit": 1.0, "recent_donation": 0.0},
                "outcome": int(same_city),
            })
        weights, version = fit_logistic_weights(rows)
        assert version == "logistic-trained-v1"
        assert weights["same_city"] > PRIOR_WEIGHTS["same_city"]

    def test_unknown_feature_names_ignored_during_training(self):
        rows = [
            {
                "features": {"same_city": 1.0, "available": 1.0, "urgency": 0.75, "age_fit": 1.0, "recent_donation": 0.0, "rogue_feature": 5.0},
                "outcome": 1,
            }
            for _ in range(20)
        ]
        weights, _ = fit_logistic_weights(rows)
        assert "rogue_feature" not in weights
