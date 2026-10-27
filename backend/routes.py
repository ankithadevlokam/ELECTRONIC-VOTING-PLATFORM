
import hmac

from flask import (
    Blueprint, current_app, jsonify, request, session
)

from backend.election import (
    get_election,
    validate_ballot,
    ElectionValidationError,
)
from backend.issuance import (
    issue_voting_credential,
    CredentialIssuanceError,
)
from backend.ballot_service import submit_ballot
from backend.consumption import CredentialValidationError


voting_api = Blueprint("voting_api", __name__)


@voting_api.get("/api/elections/current")
def current_election():
    return jsonify(get_election(1)), 200


@voting_api.post("/api/credentials/issue")
def issue_credential_endpoint():
    voter_id = session.get("voter_id")

    if type(voter_id) is not int or voter_id < 1:
        return jsonify({"error": "Authentication required"}), 401

    expected_token = session.get("csrf_token")
    supplied_token = request.headers.get("X-CSRF-Token", "")

    if (
        not isinstance(expected_token, str)
        or not expected_token
        or not hmac.compare_digest(expected_token, supplied_token)
    ):
        return jsonify({"error": "Request verification failed"}), 403

    try:
        credential = issue_voting_credential(voter_id)
    except CredentialIssuanceError:
        return jsonify({"error": "Credential issuance not permitted"}), 403

    return jsonify({
        "status": "success",
        "credential": credential,
    }), 201


def get_ballot_encryptor():
    # Test-only dependency injection; never use mock encryption
    # in the normal application.
    if current_app.testing:
        return current_app.config.get("TEST_BALLOT_ENCRYPTOR")

    try:
        from backend.encryption import encrypt_ballot
        return encrypt_ballot
    except ImportError:
        return None


@voting_api.post("/api/ballots")
def submit_ballot_endpoint():
    if not request.is_json:
        return jsonify({
            "error": "Content-Type must be application/json"
        }), 415

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON request"}), 400

    credential = data.get("credential")
    election_id = data.get("election_id")
    preferences = data.get("preferences")

    if not isinstance(credential, str) or not credential:
        return jsonify({"error": "Invalid voting credential"}), 400

    if type(election_id) is not int or election_id < 1:
        return jsonify({"error": "Invalid election ID"}), 400

    try:
        validate_ballot(election_id, preferences)
    except ElectionValidationError:
        return jsonify({"error": "Invalid ballot"}), 400

    encryptor = get_ballot_encryptor()

    if not callable(encryptor):
        return jsonify({
            "error": "Ballot submission is not yet available"
        }), 503

    try:
        result = submit_ballot(
            credential=credential,
            preferences=preferences,
            encrypt_ballot=encryptor,
            election_id=election_id,
        )
    except CredentialValidationError:
        return jsonify({
            "error": "Credential invalid or already used"
        }), 403
    except ElectionValidationError:
        return jsonify({"error": "Invalid ballot"}), 400
    except Exception:
        current_app.logger.error(
            "Ballot submission failed; transaction rolled back"
        )
        return jsonify({
            "error": "Ballot submission could not be completed"
        }), 503

    return jsonify(result), 201
