from sqlalchemy import update

from backend.models import db, VotingCredential
from backend.security import hash_voting_credential


class CredentialValidationError(Exception):
    pass


def consume_voting_credential(credential):
    """
    Mark a valid credential as used.

    Changes remain in the current database transaction.
    The caller must commit together with ballot storage,
    or roll back if ballot submission fails.
    """

    if not isinstance(credential, str) or not credential:
        raise CredentialValidationError(
            "Invalid voting credential"
        )

    credential_hash = hash_voting_credential(credential)

    result = db.session.execute(
        update(VotingCredential)
        .where(
            VotingCredential.credential_hash == credential_hash,
            VotingCredential.is_used.is_(False),
        )
        .values(is_used=True)
    )

    if result.rowcount != 1:
        raise CredentialValidationError(
            "Invalid or previously used voting credential"
        )

    return True