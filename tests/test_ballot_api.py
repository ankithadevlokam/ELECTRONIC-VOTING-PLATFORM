
import pytest
from flask import Flask

from backend.models import db, Ballot, VotingCredential
from backend.routes import voting_api
from backend.security import (
    generate_voting_credential,
    hash_voting_credential,
)


def mock_encrypt(plaintext):
    # Test substitute only; not real encryption.
    return b"TEST-CIPHERTEXT:" + plaintext


@pytest.fixture
def environment():
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SECRET_KEY="test-only-secret",
        SQLALCHEMY_DATABASE_URI="sqlite://",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        TEST_BALLOT_ENCRYPTOR=mock_encrypt,
    )

    db.init_app(app)
    app.register_blueprint(voting_api)

    with app.app_context():
        db.create_all()
        yield app.test_client(), app
        db.session.remove()
        db.drop_all()


def create_credential():
    credential = generate_voting_credential()
    db.session.add(
        VotingCredential(
            credential_hash=hash_voting_credential(credential),
            is_used=False,
        )
    )
    db.session.commit()
    return credential


def send_ballot(client, credential, preferences=None):
    if preferences is None:
        preferences = [3, 1, 2]

    return client.post(
        "/api/ballots",
        json={
            "credential": credential,
            "election_id": 1,
            "preferences": preferences,
        },
    )


def test_successful_submission(environment):
    client, app = environment
    credential = create_credential()

    response = send_ballot(client, credential)

    assert response.status_code == 201
    assert response.get_json()["status"] == "success"
    assert Ballot.query.count() == 1
    assert VotingCredential.query.first().is_used is True


def test_duplicate_submission_rejected(environment):
    client, app = environment
    credential = create_credential()

    first = send_ballot(client, credential)
    second = send_ballot(client, credential)

    assert first.status_code == 201
    assert second.status_code == 403
    assert Ballot.query.count() == 1


def test_invalid_candidate_rejected(environment):
    client, app = environment
    credential = create_credential()

    response = send_ballot(client, credential, [1, 2, 99])

    assert response.status_code == 400
    assert Ballot.query.count() == 0
    assert VotingCredential.query.first().is_used is False


def test_invalid_credential_rejected(environment):
    client, app = environment

    response = send_ballot(client, "unknown-credential")

    assert response.status_code == 403
    assert Ballot.query.count() == 0


def test_encryption_unavailable_fails_closed(environment):
    client, app = environment
    credential = create_credential()

    app.config["TEST_BALLOT_ENCRYPTOR"] = None

    response = send_ballot(client, credential)

    assert response.status_code == 503
    assert Ballot.query.count() == 0
    assert VotingCredential.query.first().is_used is False


def test_encryption_failure_rolls_back(environment):
    client, app = environment
    credential = create_credential()

    def failing_encrypt(plaintext):
        raise RuntimeError("Simulated encryption failure")

    app.config["TEST_BALLOT_ENCRYPTOR"] = failing_encrypt

    response = send_ballot(client, credential)

    assert response.status_code == 503
    assert Ballot.query.count() == 0
    assert VotingCredential.query.first().is_used is False
