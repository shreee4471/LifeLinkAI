from services.matching_service import (
    calculate_match_score,
    is_blood_compatible,
    rank_donors_for_request,
)


REQUEST = {
    "blood_group_needed": "A+",
    "city": "Pune",
    "urgency": "Critical",
}


def donor(**overrides):
    value = {
        "id": 1,
        "full_name": "Test Donor",
        "blood_group": "A+",
        "city": "Pune",
        "availability": "Available",
        "age": 28,
    }
    value.update(overrides)
    return value


def test_compatibility_matrix_filters_incompatible_donors():
    assert is_blood_compatible("A+", "O-")
    assert not is_blood_compatible("A+", "B+")
    assert calculate_match_score(REQUEST, donor(blood_group="B+")) == 0


def test_same_city_and_availability_change_probability():
    local = calculate_match_score(REQUEST, donor())
    distant = calculate_match_score(
        REQUEST,
        donor(city="Delhi", availability="Unavailable")
    )
    assert local > distant


def test_ranking_is_explainable_and_ordered():
    results = rank_donors_for_request(
        REQUEST,
        [donor(id=1), donor(id=2, city="Delhi"), donor(id=3, blood_group="B+")]
    )
    assert [item["donor"]["id"] for item in results] == [1, 2]
    assert results[0]["score"] > results[1]["score"]
    assert "Compatible blood group" in results[0]["explanation"]
    assert results[0]["probability"] <= 1
