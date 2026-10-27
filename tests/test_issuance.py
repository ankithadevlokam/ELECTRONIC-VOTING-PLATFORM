import pytest
from flask import Flask

from backend.models import db, Voter, VotingCredential
from backend.issuance import (
    issue_voting_credential,
    CredentialIssuanceError,
)
from backend.security import hash_voting_credential


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


def create_voter(reference, eligible=True):
    voter = Voter(
        voter_reference=reference,
        is_eligible=eligible,
        credential_issued=False,
    )

    db.session.add(voter)
    db.session.commit()

    return voter.id


def test_eligible_voter_receives_credential(database):
    voter_id = create_voter("VOTER001")

    credential = issue_voting_credential(voter_id)

    voter = db.session.get(Voter, voter_id)
    records = VotingCredential.query.all()

    assert isinstance(credential, str)
    assert voter.credential_issued is True
    assert len(records) == 1
    assert records[0].credential_hash == hash_voting_credential(
        credential
    )


def test_ineligible_voter_cannot_receive_credential(database):
    voter_id = create_voter("VOTER002", eligible=False)

    with pytest.raises(CredentialIssuanceError):
        issue_voting_credential(voter_id)

    assert VotingCredential.query.count() == 0


def test_duplicate_issuance_is_rejected(database):
    voter_id = create_voter("VOTER003")

    issue_voting_credential(voter_id)

    with pytest.raises(CredentialIssuanceError):
        issue_voting_credential(voter_id)

    assert VotingCredential.query.count() == 1


def test_failed_issuance_rolls_back(database, monkeypatch):
    voter_id = create_voter("VOTER004")

    def simulated_failure():
        raise RuntimeError("Simulated credential generation failure")

    monkeypatch.setattr(
        "backend.issuance.generate_voting_credential",
        simulated_failure,
    )

    with pytest.raises(RuntimeError):
        issue_voting_credential(voter_id)

    db.session.expire_all()

    voter = db.session.get(Voter, voter_id)

    assert voter.credential_issued is False
    assert VotingCredential.query.count() == 0