from flask import Flask, jsonify
import os
from backend.models import db


def create_app():
    app = Flask(__name__)

    # Local prototype database
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///voting.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["VOTING_ENCRYPTION_KEY"] = os.environ.get("VOTING_ENCRYPTION_KEY")

    # Connect SQLAlchemy to Flask
    db.init_app(app)

    # Import models before creating database tables
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
