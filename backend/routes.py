
from flask import Blueprint, jsonify, request
from backend.election import get_election

voting_api = Blueprint("voting_api", __name__)

@voting_api.get("/api/elections/current")
def current_election():
    election = get_election(1)
    return jsonify(election), 200
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

    if (
        not isinstance(preferences, list)
        or not preferences
        or any(type(p) is not int or p < 1 for p in preferences)
        or len(preferences) != len(set(preferences))
    ):
        return jsonify({"error": "Invalid ballot preferences"}), 400

    # Fail closed until election validation and real encryption
    # have been integrated and security-tested.
    return jsonify({
        "error": "Ballot submission is not yet available"
    }), 503

import hmac
from flask import session

from backend.issuance import (
    issue_voting_credential,
    CredentialIssuanceError,
)


@voting_api.post("/api/credentials/issue")
def issue_credential_endpoint():
    # Identity must come from the trusted authentication session.
    voter_id = session.get("voter_id")

    if type(voter_id) is not int or voter_id < 1:
        return jsonify({
            "error": "Authentication required"
        }), 401

    # CSRF token must have been created by the trusted login flow.
    expected_token = session.get("csrf_token")
    supplied_token = request.headers.get("X-CSRF-Token", "")

    if (
        not isinstance(expected_token, str)
        or not expected_token
        or not hmac.compare_digest(expected_token, supplied_token)
    ):
        return jsonify({
            "error": "Request verification failed"
        }), 403

    try:
        credential = issue_voting_credential(voter_id)

    except CredentialIssuanceError:
        return jsonify({
            "error": "Credential issuance not permitted"
        }), 403

    return jsonify({
        "status": "success",
        "credential": credential
    }), 201
