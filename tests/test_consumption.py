import pytest
from flask import Flask

from backend.models import db, VotingCredential
from backend.security import (
    generate_voting_credential,
    hash_voting_credential,
)
from backend.consumption import (
    consume_voting_credential,
    CredentialValidationError,
)


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


def create_credential():
    credential = generate_voting_credential()

    record = VotingCredential(
        credential_hash=hash_voting_credential(credential),
        is_used=False,
    )

    db.session.add(record)
    db.session.commit()
    return credential


def test_valid_credential_consumed(database):
    credential = create_credential()

    assert consume_voting_credential(credential) is True
    db.session.commit()

    record = VotingCredential.query.first()
    assert record.is_used is True


def test_credential_cannot_be_reused(database):
    credential = create_credential()

    consume_voting_credential(credential)
    db.session.commit()

    with pytest.raises(CredentialValidationError):
        consume_voting_credential(credential)

    db.session.rollback()


def test_invalid_credential_rejected(database):
    create_credential()

    with pytest.raises(CredentialValidationError):
        consume_voting_credential("invalid-credential")

    db.session.rollback()


def test_empty_credential_rejected(database):
    with pytest.raises(CredentialValidationError):
        consume_voting_credential("")


def test_credential_consumption_rolls_back(database):
    credential = create_credential()

    consume_voting_credential(credential)

    # Simulate a ballot submission failure.
    db.session.rollback()
    db.session.expire_all()

    record = VotingCredential.query.first()
    assert record.is_used is False