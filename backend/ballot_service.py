
import json

from backend.models import db, Ballot
from backend.consumption import consume_voting_credential
from backend.election import validate_ballot


class BallotSubmissionError(Exception):
    pass


def submit_ballot(
    credential,
    preferences,
    encrypt_ballot,
    election_id=1,
):
    """
    Validate, encrypt and store an anonymous ballot.

    Credential consumption and ballot insertion take place
    in the same database transaction.
    """

    # Validate the selected election and candidate rankings.
    validate_ballot(election_id, preferences)

    try:
        ballot_data = json.dumps(
            {
                "election_id": election_id,
                "preferences": preferences,
            },
            separators=(",", ":"),
        ).encode("utf-8")

        # The encryption function is supplied by the encryption module.
        encrypted_data = encrypt_ballot(ballot_data)

        if not isinstance(encrypted_data, bytes) or not encrypted_data:
            raise BallotSubmissionError(
                "Ballot encryption failed"
            )

        # Mark the credential as used without committing yet.
        consume_voting_credential(credential)

        # Store ciphertext without a voter ID or credential reference.
        db.session.add(
            Ballot(encrypted_vote=encrypted_data)
        )

        # Commit both operations together.
        db.session.commit()

        return {"status": "success"}

    except Exception:
        db.session.rollback()
        raise
