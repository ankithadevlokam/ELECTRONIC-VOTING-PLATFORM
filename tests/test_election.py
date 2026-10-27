
import pytest

from backend.election import (
    get_election,
    validate_ballot,
    ElectionValidationError,
)


def test_valid_election_exists():
    election = get_election(1)

    assert election["id"] == 1
    assert len(election["candidates"]) == 3


def test_valid_candidate_preferences():
    assert validate_ballot(1, [3, 1, 2]) is True


def test_unknown_candidate_rejected():
    with pytest.raises(ElectionValidationError):
        validate_ballot(1, [1, 2, 99])


def test_duplicate_preferences_rejected():
    with pytest.raises(ElectionValidationError):
        validate_ballot(1, [1, 1, 2])


def test_incomplete_preferences_rejected():
    with pytest.raises(ElectionValidationError):
        validate_ballot(1, [1, 2])


def test_unknown_election_rejected():
    with pytest.raises(ElectionValidationError):
        validate_ballot(999, [1, 2, 3])


def test_boolean_candidate_id_rejected():
    with pytest.raises(ElectionValidationError):
        validate_ballot(1, [True, 2, 3])
def test_election_get_api():
    from backend.app import app

    with app.test_client() as client:
        response = client.get("/api/elections/current")

        assert response.status_code == 200

        data = response.get_json()

        assert data["id"] == 1
        assert len(data["candidates"]) == 3
        assert data["name"] == "Demonstration House Election"