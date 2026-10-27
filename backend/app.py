
import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, jsonify

from backend.models import db


load_dotenv()


def create_app():
    app = Flask(__name__)

    # Authentication configuration
    app.config["SECRET_KEY"] = os.getenv("APP_SECRET_KEY")
    app.config["DEV_AUTH_ENABLED"] = (
        os.getenv("DEV_AUTH_ENABLED", "false").lower() == "true"
    )
    app.config["DEV_VOTER_REFERENCE"] = os.getenv(
        "DEV_VOTER_REFERENCE", ""
    )
    app.config["DEV_VOTER_PASSWORD_HASH"] = os.getenv(
        "DEV_VOTER_PASSWORD_HASH", ""
    )

    # Session security
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = (
        os.getenv("APP_USE_HTTPS", "false").lower() == "true"
    )
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
        minutes=15
    )

    if app.config["DEV_AUTH_ENABLED"] and not app.config["SECRET_KEY"]:
        raise RuntimeError(
            "APP_SECRET_KEY is required when development login is enabled"
        )

    # Local prototype database
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///voting.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Initialise database
    db.init_app(app)

    # Register REST API routes
    from backend.routes import voting_api
    app.register_blueprint(voting_api)

    # Register authentication routes
    from backend.auth import auth_api
    app.register_blueprint(auth_api)

    # Create database tables
    from backend.models import Voter, VotingCredential, Ballot

    with app.app_context():
        db.create_all()

    @app.get("/api/health")
    def health_check():
        return jsonify({
            "status": "success",
            "message": "Electronic Voting Platform API is running"
        }), 200

    return app


app = create_app()
