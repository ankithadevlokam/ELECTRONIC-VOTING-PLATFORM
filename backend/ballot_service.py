
import json

from backend.models import db, Ballot
from backend.consumption import consume_voting_credential


class BallotSubmissionError(Exception):
    pass


def submit_ballot(credential, preferences, encrypt_ballot):
    """
    Encrypt and store a ballot while consuming its credential
    in the same database transaction.

    The encryption function is supplied separately.
    """

    if (
        not isinstance(preferences, list)
        or not preferences
        or any(type(p) is not int or p < 1 for p in preferences)
        or len(preferences) != len(set(preferences))
    ):
        raise BallotSubmissionError("Invalid ballot preferences")

    try:
        ballot_data = json.dumps(
            {"preferences": preferences},
            separators=(",", ":")
        ).encode("utf-8")

        encrypted_data = encrypt_ballot(ballot_data)

        if not isinstance(encrypted_data, bytes) or not encrypted_data:
            raise BallotSubmissionError("Ballot encryption failed")

        consume_voting_credential(credential)

        db.session.add(Ballot(encrypted_vote=encrypted_data))
        db.session.commit()

        return {"status": "success"}

    except Exception:
        db.session.rollback()
        raise
