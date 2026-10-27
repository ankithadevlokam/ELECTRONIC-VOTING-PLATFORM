
import os
from flask import Flask, jsonify

from backend.models import db


def create_app():
    # Find the root directory of the repository.
    base_dir = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )

    # Tell Flask where the separate frontend files are located.
    app = Flask(
        __name__,
        template_folder=os.path.join(
            base_dir, "frontend", "templates"
        ),
        static_folder=os.path.join(
            base_dir, "frontend", "static"
        ),
        static_url_path="/static",
    )

    # Local prototype database.
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///voting.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Connect SQLAlchemy to Flask.
    db.init_app(app)

    # Import models before creating database tables.
    from backend.models import Voter, VotingCredential, Ballot

    with app.app_context():
        db.create_all()

    # Register voting endpoints.
    from backend.routes import voting_bp
    app.register_blueprint(voting_bp)

    @app.get("/")
    def home():
        from flask import render_template
        return render_template("index.html")

    @app.get("/api/health")
    def health_check():
        return jsonify({
            "status": "success",
            "message": "Electronic Voting Platform API is running"
        }), 200

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
