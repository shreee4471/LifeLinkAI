import os
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DB_MODULES = [
    "utils.db_connection",
    "database.create_db",
    "models.user_model",
    "models.donor_model",
    "models.blood_request_model",
    "models.match_model",
    "models.trust_model",
    "services.audit_service",
]

APP_MODULES = [
    "app",
    "routes.auth_routes",
    "routes.dashboard_routes",
    "routes.profile_routes",
    "routes.donor_routes",
    "routes.request_routes",
    "routes.match_routes",
    "routes.admin_routes",
    "services.matching_service",
]


@pytest.fixture()
def temp_db(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = str(Path(tmp_dir) / "test.db")
        monkeypatch.setenv("LIFELINK_DATABASE", db_path)
        # db_connection resolves DATABASE at import time, so reimport the DB
        # layer against the patched env var
        for module_name in DB_MODULES:
            sys.modules.pop(module_name, None)
        import utils.db_connection

        assert utils.db_connection.DATABASE == db_path
        import database.create_db

        database.create_db.main()
        yield db_path
        for module_name in DB_MODULES:
            sys.modules.pop(module_name, None)


@pytest.fixture()
def app_client(temp_db):
    monkeypatch_secret = os.environ.get("SECRET_KEY")
    os.environ["SECRET_KEY"] = "test-secret-key"
    for module_name in APP_MODULES:
        sys.modules.pop(module_name, None)
    import app as app_module

    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        yield client
    if monkeypatch_secret is None:
        os.environ.pop("SECRET_KEY", None)
    else:
        os.environ["SECRET_KEY"] = monkeypatch_secret
    for module_name in APP_MODULES:
        sys.modules.pop(module_name, None)


@pytest.fixture()
def seeded_db(temp_db):
    from models.donor_model import Donor
    from models.trust_model import Trust
    from models.user_model import User

    User.create_user("admin", "admin@example.com", "hash-admin")
    User.set_role(1, "admin")
    User.create_user("requester", "requester@example.com", "hash-req")
    User.create_user("donor1", "donor1@example.com", "hash-d1")
    User.create_user("donor2", "donor2@example.com", "hash-d2")

    Donor.create_donor(3, "Donor One", "O-", "Mumbai", "1111111111", 30)
    Donor.create_donor(4, "Donor Two", "A+", "Mumbai", "2222222222", 45)
    Trust.set_donor_verification(1, "Verified", "Verified", 1)
    Trust.set_donor_verification(2, "Verified", "Verified", 1)

    return temp_db
