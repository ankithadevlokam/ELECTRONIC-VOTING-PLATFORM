
import pytest
from flask import Flask

from backend.models import db, Voter, VotingCredential
from backend.routes import voting_api


@pytest.fixture
def environment():
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SECRET_KEY="testing-only-secret",
        SQLALCHEMY_DATABASE_URI="sqlite://",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    db.init_app(app)
    app.register_blueprint(voting_api)

    with app.app_context():
        db.create_all()

        yield app.test_client()

        db.session.remove()
        db.drop_all()


def create_voter(reference, eligible=True):
    voter = Voter(
        voter_reference=reference,
        is_eligible=eligible,
        credential_issued=False,
    )
    db.session.add(voter)
    db.session.commit()
    return voter.id


def authenticate_test_session(client, voter_id):
    # Direct session injection is permitted only in tests.
    with client.session_transaction() as user_session:
        user_session["voter_id"] = voter_id
        user_session["csrf_token"] = "test-csrf-token"


def issue_request(client, token="test-csrf-token", body=None):
    return client.post(
        "/api/credentials/issue",
        json={} if body is None else body,
        headers={"X-CSRF-Token": token},
    )


def test_unauthenticated_issuance_rejected(environment):
    response = issue_request(environment)

    assert response.status_code == 401


def test_eligible_authenticated_voter(environment):
    voter_id = create_voter("API-VOTER-001")
    authenticate_test_session(environment, voter_id)

    response = issue_request(environment)

    assert response.status_code == 201
    assert response.get_json()["status"] == "success"
    assert response.get_json()["credential"]
    assert VotingCredential.query.count() == 1


def test_repeat_issuance_rejected(environment):
    voter_id = create_voter("API-VOTER-002")
    authenticate_test_session(environment, voter_id)

    first = issue_request(environment)
    second = issue_request(environment)

    assert first.status_code == 201
    assert second.status_code == 403
    assert VotingCredential.query.count() == 1


def test_ineligible_voter_rejected(environment):
    voter_id = create_voter(
        "API-VOTER-003", eligible=False
    )
    authenticate_test_session(environment, voter_id)

    response = issue_request(environment)

    assert response.status_code == 403
    assert VotingCredential.query.count() == 0


def test_missing_or_invalid_csrf_rejected(environment):
    voter_id = create_voter("API-VOTER-004")
    authenticate_test_session(environment, voter_id)

    response = issue_request(environment, "incorrect-token")

    assert response.status_code == 403
    assert VotingCredential.query.count() == 0


def test_client_supplied_voter_id_cannot_override_session(environment):
    allowed_id = create_voter("API-VOTER-005")
    blocked_id = create_voter("API-VOTER-006", eligible=False)

    authenticate_test_session(environment, allowed_id)

    response = issue_request(
        environment,
        body={"voter_id": blocked_id},
    )

    assert response.status_code == 201
    assert db.session.get(Voter, allowed_id).credential_issued is True
    assert db.session.get(Voter, blocked_id).credential_issued is False
