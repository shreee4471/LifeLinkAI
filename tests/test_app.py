"""Integration tests: auth, request flow, matching, outcomes, cooldown, admin, retrain."""


def _login(client, user_id, username, email, role):
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["username"] = username
        session["email"] = email
        session["role"] = role
        session["csrf_token"] = "test-csrf"


class TestAuthFlow:
    def test_register_shows_verification_link_when_smtp_unconfigured(self, app_client):
        with app_client.session_transaction() as session:
            session["csrf_token"] = "test-csrf"
        response = app_client.post("/register", data={
            "username": "alice",
            "email": "alice@example.com",
            "password": "secret123",
            "confirm_password": "secret123",
            "csrf_token": "test-csrf",
        }, follow_redirects=True)
        assert response.status_code == 200
        text = response.get_data(as_text=True)
        assert "Registration successful" in text
        assert "/verify-email/" in text

    def test_duplicate_email_rejected(self, app_client):
        with app_client.session_transaction() as session:
            session["csrf_token"] = "test-csrf"
        app_client.post("/register", data={
            "username": "alice", "email": "alice@example.com",
            "password": "secret123", "confirm_password": "secret123",
            "csrf_token": "test-csrf",
        })
        response = app_client.post("/register", data={
            "username": "alice2", "email": "alice@example.com",
            "password": "secret123", "confirm_password": "secret123",
            "csrf_token": "test-csrf",
        }, follow_redirects=True)
        assert b"Email already registered" in response.data

    def test_csrf_enforced_on_post(self, app_client):
        response = app_client.post("/login", data={"email": "x@y.z", "password": "x"})
        assert response.status_code == 400


class TestMatchingFlow:
    def test_full_request_to_match_flow(self, seeded_db, app_client):
        from models.blood_request_model import BloodRequest
        from models.donor_model import Donor
        from models.match_model import Match
        from models.trust_model import Trust

        _login(app_client, 2, "requester", "requester@example.com", "user")

        # Make both donors available so get_available_donors() returns them
        Donor.update_availability(3, "Available")
        Donor.update_availability(4, "Available")

        # Request starts pending hospital review; a reviewer approves it
        request_id = BloodRequest.create_request(2, "O-", "Mumbai", "City Hospital", 2, "Critical")
        assert Trust.verify_hospital_request(request_id, 1)

        # The route requires the requester's contact-disclosure consent,
        # which the create-request route would have granted
        Trust.grant_consent(2, "donor_contact_disclosure", "v1", "test-hash")

        response = app_client.post(
            f"/requests/{request_id}/matches/generate",
            headers={"X-CSRF-Token": "test-csrf"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        text = response.get_data(as_text=True)
        # Donor One (O-, same city) matches; Donor Two (A+) is incompatible with O-
        assert "Donor One" in text
        assert "Donor Two" not in text

        # Label the outcome
        matches = Match.get_matches_for_request(request_id)
        assert len(matches) == 1
        match_id = matches[0]["id"]
        assert matches[0]["features"]  # features persisted for training

        response = app_client.post(
            f"/matches/{match_id}/outcome",
            data={"outcome": "1", "csrf_token": "test-csrf"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        labeled = Match.get_labeled_outcomes()
        assert len(labeled) == 1
        assert labeled[0]["outcome"] == 1

    def test_outcome_cannot_be_relabeled(self, seeded_db, app_client):
        from models.blood_request_model import BloodRequest
        from models.match_model import Match

        _login(app_client, 2, "requester", "requester@example.com", "user")

        request_id = BloodRequest.create_request(2, "A+", "Mumbai", "City Hospital", 1, "High")
        Match.create_match(request_id, 2, 85.0, "test", features={"same_city": 1.0}, model_version="logistic-prior-v1")

        match_id = Match.get_matches_for_request(request_id)[0]["id"]
        assert app_client.post(f"/matches/{match_id}/outcome", data={"outcome": "1", "csrf_token": "test-csrf"})
        assert Match.record_outcome(match_id, 0) is False

    def test_non_owner_cannot_generate_matches(self, seeded_db, app_client):
        from models.blood_request_model import BloodRequest

        _login(app_client, 3, "donor1", "donor1@example.com", "user")

        request_id = BloodRequest.create_request(2, "O-", "Mumbai", "City Hospital", 2, "Critical")
        response = app_client.post(
            f"/requests/{request_id}/matches/generate",
            headers={"X-CSRF-Token": "test-csrf"},
            follow_redirects=True,
        )
        assert b"Only the requester can generate matches" in response.data


class TestDonationCooldownFlow:
    def test_logging_donation_sets_cooldown_and_unavailable(self, seeded_db, app_client):
        from models.donor_model import Donor
        from services.matching_service import days_since_last_donation

        _login(app_client, 3, "donor1", "donor1@example.com", "user")

        response = app_client.post(
            "/donor/donations/log",
            headers={"X-CSRF-Token": "test-csrf"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Donation recorded" in response.data

        donor = Donor.get_donor_by_user_id(3)
        assert donor["last_donation_at"] is not None
        assert donor["availability"] == "Unavailable"
        assert days_since_last_donation(donor) == 0


class TestAdminFlow:
    def test_admin_dashboard_lists_pending(self, seeded_db, app_client):
        from models.donor_model import Donor
        from models.user_model import User

        _login(app_client, 1, "admin", "admin@example.com", "admin")

        User.create_user("donor3", "donor3@example.com", "hash-d3")
        Donor.create_donor(5, "Donor Three", "B+", "Pune", "3333333333", 28)

        response = app_client.get("/admin")
        assert response.status_code == 200
        assert b"Donor Three" in response.data

    def test_regular_user_forbidden_from_admin(self, seeded_db, app_client):
        _login(app_client, 2, "requester", "requester@example.com", "user")

        assert app_client.get("/admin").status_code == 403

    def test_admin_can_verify_donor(self, seeded_db, app_client):
        from models.donor_model import Donor
        from models.user_model import User

        _login(app_client, 1, "admin", "admin@example.com", "admin")

        User.create_user("donor3", "donor3@example.com", "hash-d3")
        Donor.create_donor(5, "Donor Three", "B+", "Pune", "3333333333", 28)

        response = app_client.post(
            "/admin/donors/3/verify",
            data={"decision": "approve", "csrf_token": "test-csrf"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        donor = Donor.get_donor_by_user_id(5)
        assert donor["identity_status"] == "Verified"
        assert donor["blood_type_verified_at"] is not None

    def test_admin_can_change_role(self, seeded_db, app_client):
        from models.user_model import User

        _login(app_client, 1, "admin", "admin@example.com", "admin")

        response = app_client.post(
            "/admin/users/2/role",
            data={"role": "hospital_reviewer", "csrf_token": "test-csrf"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert User.get_user_by_email("requester@example.com")["role"] == "hospital_reviewer"

    def test_admin_cannot_demote_self(self, seeded_db, app_client):
        from models.user_model import User

        _login(app_client, 1, "admin", "admin@example.com", "admin")

        response = app_client.post(
            "/admin/users/1/role",
            data={"role": "user", "csrf_token": "test-csrf"},
            follow_redirects=True,
        )
        assert b"Admins cannot demote themselves" in response.data
        assert User.get_user_by_email("admin@example.com")["role"] == "admin"


class TestRetrainFlow:
    def test_retrain_persists_model_state(self, seeded_db, app_client):
        from models.blood_request_model import BloodRequest
        from models.match_model import Match

        _login(app_client, 1, "admin", "admin@example.com", "admin")

        request_id = BloodRequest.create_request(2, "A+", "Mumbai", "City Hospital", 1, "High")
        features = {"same_city": 1.0, "available": 1.0, "urgency": 0.75, "age_fit": 1.0, "recent_donation": 0.0}
        Match.create_match(request_id, 1, 90.0, "test", features=features, model_version="logistic-prior-v1")

        response = app_client.post(
            "/model/retrain",
            headers={"X-CSRF-Token": "test-csrf"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        state = Match.get_model_state()
        assert state is not None
        assert state["labeled_outcomes"] == 0
        assert b"prior is still in use" in response.data
