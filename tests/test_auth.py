
import pytest
from argon2 import PasswordHasher
from flask import Flask

from backend.auth import auth_api
from backend.routes import voting_api
from backend.models import db, Voter, VotingCredential


TEST_PASSWORD = "LocalDemoPassword123!"


@pytest.fixture
def environment():
    app = Flask(__name__)

    app.config.update(
        TESTING=True,
        SECRET_KEY="test-only-session-secret",
        SQLALCHEMY_DATABASE_URI="sqlite://",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        DEV_AUTH_ENABLED=True,
        DEV_VOTER_REFERENCE="DEMO001",
        DEV_VOTER_PASSWORD_HASH=PasswordHasher().hash(
            TEST_PASSWORD
        ),
    )

    db.init_app(app)
    app.register_blueprint(auth_api)
    app.register_blueprint(voting_api)

    with app.app_context():
        db.create_all()

        voter = Voter(
            voter_reference="DEMO001",
            is_eligible=True,
            credential_issued=False,
        )
        db.session.add(voter)
        db.session.commit()

        yield app.test_client(), app

        db.session.remove()
        db.drop_all()


def login(client, password=TEST_PASSWORD):
    return client.post(
        "/api/auth/login",
        json={
            "voter_reference": "DEMO001",
            "password": password,
        },
    )


def test_valid_login_creates_session(environment):
    client, app = environment

    response = login(client)

    assert response.status_code == 200
    assert response.get_json()["status"] == "success"
    assert response.get_json()["csrf_token"]

    with client.session_transaction() as sess:
        assert isinstance(sess.get("voter_id"), int)


def test_wrong_password_rejected(environment):
    client, app = environment

    response = login(client, "IncorrectPassword")

    assert response.status_code == 401


def test_unknown_voter_rejected(environment):
    client, app = environment

    response = client.post(
        "/api/auth/login",
        json={
            "voter_reference": "UNKNOWN",
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 401


def test_login_to_credential_issuance(environment):
    client, app = environment

    login_response = login(client)
    assert login_response.status_code == 200

    csrf_token = login_response.get_json()["csrf_token"]

    issue_response = client.post(
        "/api/credentials/issue",
        json={},
        headers={"X-CSRF-Token": csrf_token},
    )

    assert issue_response.status_code == 201
    assert issue_response.get_json()["credential"]
    assert VotingCredential.query.count() == 1


def test_logout_invalidates_session(environment):
    client, app = environment

    login_response = login(client)
    csrf_token = login_response.get_json()["csrf_token"]

    response = client.post(
        "/api/auth/logout",
        headers={"X-CSRF-Token": csrf_token},
    )

    assert response.status_code == 200

    issue_response = client.post(
        "/api/credentials/issue",
        json={},
        headers={"X-CSRF-Token": csrf_token},
    )

    assert issue_response.status_code == 401


def test_login_disabled_by_default(environment):
    client, app = environment

    app.config["DEV_AUTH_ENABLED"] = False

    response = login(client)

    assert response.status_code == 503
