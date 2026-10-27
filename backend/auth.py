
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from flask import Blueprint, current_app, jsonify, request, session

from backend.models import Voter

auth_api = Blueprint("auth_api", __name__)
password_hasher = PasswordHasher()


@auth_api.post("/api/auth/login")
def voter_login():
    # This login mechanism is for the local prototype only.
    if not current_app.config.get("DEV_AUTH_ENABLED", False):
        return jsonify({"error": "Authentication unavailable"}), 503

    if not request.is_json:
        return jsonify({"error": "JSON required"}), 415

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid request"}), 400

    reference = data.get("voter_reference")
    password = data.get("password")

    if not isinstance(reference, str) or not isinstance(password, str):
        return jsonify({"error": "Invalid credentials"}), 401

    configured_reference = current_app.config.get(
        "DEV_VOTER_REFERENCE", ""
    )
    configured_hash = current_app.config.get(
        "DEV_VOTER_PASSWORD_HASH", ""
    )

    if not configured_reference or not configured_hash:
        return jsonify({"error": "Authentication unavailable"}), 503

    try:
        password_valid = password_hasher.verify(
            configured_hash, password
        )
    except (VerifyMismatchError, VerificationError, ValueError):
        password_valid = False

    reference_valid = hmac.compare_digest(
        reference.encode("utf-8"),
        configured_reference.encode("utf-8"),
    )

    if not (password_valid and reference_valid):
        return jsonify({"error": "Invalid credentials"}), 401

    voter = Voter.query.filter_by(
        voter_reference=reference,
        is_eligible=True,
    ).first()

    if voter is None:
        return jsonify({"error": "Invalid credentials"}), 401

    session.clear()
    session["voter_id"] = voter.id
    session["csrf_token"] = secrets.token_urlsafe(32)

    return jsonify({
        "status": "success",
        "csrf_token": session["csrf_token"],
    }), 200


@auth_api.post("/api/auth/logout")
def voter_logout():
    if "voter_id" not in session:
        return jsonify({"error": "Authentication required"}), 401

    expected = session.get("csrf_token", "")
    supplied = request.headers.get("X-CSRF-Token", "")

    if not expected or not hmac.compare_digest(expected, supplied):
        return jsonify({"error": "Request verification failed"}), 403

    session.clear()
    return jsonify({"status": "success"}), 200
