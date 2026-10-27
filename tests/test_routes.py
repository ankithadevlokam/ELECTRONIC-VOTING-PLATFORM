
import pytest

from backend.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def test_health_endpoint(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "success"


def test_ballot_endpoint_rejects_non_json(client):
    response = client.post(
        "/api/ballots",
        data="invalid body",
        content_type="text/plain",
    )

    assert response.status_code == 415


def test_ballot_endpoint_rejects_invalid_credential(client):
    response = client.post(
        "/api/ballots",
        json={
            "credential": "",
            "election_id": 1,
            "preferences": [1, 2, 3],
        },
    )

    assert response.status_code == 400


def test_ballot_endpoint_rejects_duplicate_preferences(client):
    response = client.post(
        "/api/ballots",
        json={
            "credential": "test",
            "election_id": 1,
            "preferences": [1, 1, 2],
        },
    )

    assert response.status_code == 400


def test_ballot_endpoint_fails_closed(client):
    response = client.post(
        "/api/ballots",
        json={
            "credential": "test",
            "election_id": 1,
            "preferences": [1, 2, 3],
        },
    )

    assert response.status_code == 503
    assert "not yet available" in response.get_json()["error"]
