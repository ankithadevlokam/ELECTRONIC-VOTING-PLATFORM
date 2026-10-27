
import pytest
from flask import Flask

from backend.models import db, Ballot, VotingCredential
from backend.security import (
    generate_voting_credential,
    hash_voting_credential,
)
from backend.ballot_service import (
    submit_ballot,
    BallotSubmissionError,
)
from backend.consumption import CredentialValidationError


@pytest.fixture
def database():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["TESTING"] = True

    db.init_app(app)

    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


def create_test_credential():
    credential = generate_voting_credential()

    db.session.add(
        VotingCredential(
            credential_hash=hash_voting_credential(credential),
            is_used=False,
        )
    )
    db.session.commit()

    return credential


def mock_encrypt(data):
    # Test-only substitute, NOT real encryption.
    return b"MOCK:" + data


def test_successful_ballot_submission(database):
    credential = create_test_credential()

    result = submit_ballot(
        credential, [3, 1, 2], mock_encrypt
    )

    assert result["status"] == "success"
    assert Ballot.query.count() == 1
    assert VotingCredential.query.first().is_used is True
    assert Ballot.query.first().encrypted_vote.startswith(b"MOCK:")


def test_duplicate_ballot_rejected(database):
    credential = create_test_credential()

    submit_ballot(credential, [1, 2, 3], mock_encrypt)

    with pytest.raises(CredentialValidationError):
        submit_ballot(credential, [2, 1, 3], mock_encrypt)

    assert Ballot.query.count() == 1


def test_invalid_preferences_rejected(database):
    credential = create_test_credential()

    with pytest.raises(ElectionValidationError):
        submit_ballot(credential, [1, 1, 2], mock_encrypt)

    assert Ballot.query.count() == 0
    assert VotingCredential.query.first().is_used is False


def test_encryption_failure_does_not_consume_credential(database):
    credential = create_test_credential()

    def failed_encryption(data):
        raise RuntimeError("Simulated encryption failure")

    with pytest.raises(RuntimeError):
        submit_ballot(
            credential, [1, 2, 3], failed_encryption
        )

    assert Ballot.query.count() == 0
    assert VotingCredential.query.first().is_used is False


def test_database_failure_rolls_back_credential(database, monkeypatch):
    credential = create_test_credential()

    def failed_commit():
        raise RuntimeError("Simulated database failure")

    monkeypatch.setattr(db.session, "commit", failed_commit)

    with pytest.raises(RuntimeError):
        submit_ballot(
            credential, [1, 2, 3], mock_encrypt
        )

    db.session.expire_all()

    assert Ballot.query.count() == 0
    assert VotingCredential.query.first().is_used is False


from backend.election import ElectionValidationError


def test_unknown_election_cannot_submit_ballot(database):
    credential = create_test_credential()

    with pytest.raises(ElectionValidationError):
        submit_ballot(
            credential,
            [1, 2, 3],
            mock_encrypt,
            election_id=999,
        )

    assert Ballot.query.count() == 0
    assert VotingCredential.query.first().is_used is False


def test_unknown_candidate_cannot_submit_ballot(database):
    credential = create_test_credential()

    with pytest.raises(ElectionValidationError):
        submit_ballot(
            credential,
            [1, 2, 99],
            mock_encrypt,
            election_id=1,
        )

    assert Ballot.query.count() == 0
    assert VotingCredential.query.first().is_used is False

