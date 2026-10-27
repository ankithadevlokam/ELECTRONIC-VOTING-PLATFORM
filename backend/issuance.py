from sqlalchemy import update

from backend.models import db, Voter, VotingCredential
from backend.security import (
    generate_voting_credential,
    hash_voting_credential,
)


class CredentialIssuanceError(Exception):
    pass


def issue_voting_credential(voter_id):
    """
    Issue one voting credential to an eligible voter.

    voter_id must come from a trusted authentication layer,
    not directly from an unverified client request.
    """

    try:
        # Atomically reserve issuance for an eligible voter.
        result = db.session.execute(
            update(Voter)
            .where(
                Voter.id == voter_id,
                Voter.is_eligible.is_(True),
                Voter.credential_issued.is_(False),
            )
            .values(credential_issued=True)
        )

        if result.rowcount != 1:
            db.session.rollback()
            raise CredentialIssuanceError(
                "Voter is ineligible or already issued a credential"
            )

        # Generate a random credential.
        credential = generate_voting_credential()

        # Store only its hash, without a voter reference.
        credential_record = VotingCredential(
            credential_hash=hash_voting_credential(credential),
            is_used=False,
        )

        db.session.add(credential_record)

        # Commit the voter flag and credential together.
        db.session.commit()

        return credential

    except CredentialIssuanceError:
        raise

    except Exception:
        db.session.rollback()
        raise