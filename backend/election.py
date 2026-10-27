
# Demonstration election data for the SR07 prototype.
# Replace with validated election records during integration.

ELECTIONS = {
    1: {
        "id": 1,
        "name": "Demonstration House Election",
        "candidates": [
            {"id": 1, "name": "Candidate A"},
            {"id": 2, "name": "Candidate B"},
            {"id": 3, "name": "Candidate C"},
        ],
    }
}


class ElectionValidationError(ValueError):
    pass


def get_election(election_id):
    if type(election_id) is not int:
        raise ElectionValidationError("Invalid election")

    election = ELECTIONS.get(election_id)

    if election is None:
        raise ElectionValidationError("Election not found")

    return election


def validate_ballot(election_id, preferences):
    election = get_election(election_id)

    candidate_ids = {
        candidate["id"]
        for candidate in election["candidates"]
    }

    if (
        not isinstance(preferences, list)
        or len(preferences) != len(candidate_ids)
        or any(type(p) is not int for p in preferences)
        or set(preferences) != candidate_ids
    ):
        raise ElectionValidationError(
            "Invalid candidate preferences"
        )

    return True
