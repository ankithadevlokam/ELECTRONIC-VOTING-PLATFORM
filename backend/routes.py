
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
