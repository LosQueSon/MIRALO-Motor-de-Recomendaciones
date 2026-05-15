from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture()
def client() -> TestClient:
    main.service.room_polls.clear()
    with TestClient(main.app) as test_client:
        yield test_client


def _top_item(payload: dict[str, Any]) -> dict[str, Any]:
    return payload["recommendations"][0]


def _genre_overlap(item: dict[str, Any], expected_genres: set[str]) -> set[str]:
    return set(item["genres"]).intersection(expected_genres)


def test_room_recommendations_are_coherent_for_animation_and_children(client: TestClient) -> None:
    payload = [
        {"userId": "69bb3d5ee1db9d17817b70cb", "favoriteGenre": "Animation"},
        {"userId": "69bde9c6c661ee886a15e702", "favoriteGenre": "Children"},
    ]

    response = client.post("/recommendations/room", json=payload)

    assert response.status_code == 200
    body = response.json()

    assert body["success"] is True
    assert body["totalUsers"] == 2
    assert body["recommendationCount"] == 10

    top = _top_item(body)
    assert _genre_overlap(top, {"Animation", "Children"})
    assert "Coincide con los géneros de la sala" in top["reasons"][0]


def test_room_recommendations_change_when_genres_are_alternated(client: TestClient) -> None:
    payload_animation_children = [
        {"userId": "69bb3d5ee1db9d17817b70cb", "favoriteGenre": "Animation"},
        {"userId": "69bde9c6c661ee886a15e702", "favoriteGenre": "Children"},
    ]
    payload_action_scifi = [
        {"userId": "69bb3d5ee1db9d17817b70cb", "favoriteGenre": "Action"},
        {"userId": "69bde9c6c661ee886a15e702", "favoriteGenre": "Sci-Fi"},
    ]

    response_a = client.post("/recommendations/room", json=payload_animation_children)
    response_b = client.post("/recommendations/room", json=payload_action_scifi)

    assert response_a.status_code == 200
    assert response_b.status_code == 200

    body_a = response_a.json()
    body_b = response_b.json()

    top_a = _top_item(body_a)
    top_b = _top_item(body_b)

    assert _genre_overlap(top_a, {"Animation", "Children"})
    assert _genre_overlap(top_b, {"Action", "Sci-Fi"})
    assert top_a["movieId"] != top_b["movieId"]
    assert top_a["title"] != top_b["title"]


def test_room_alias_accepts_object_payload_with_users_and_topk(client: TestClient) -> None:
    payload = {
        "users": [
            {"userId": "u1", "favoriteGenre": "Animation"},
            {"userId": "u2", "favoriteGenre": "Children"},
        ],
        "topK": 3,
    }

    response = client.post("/ml/predict-room", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["recommendationCount"] == 3
    assert _genre_overlap(_top_item(body), {"Animation", "Children"})


def test_room_poll_uses_top_three_recommendations_and_majority_wins(client: TestClient) -> None:
    payload = [
        {"userId": "69bb3d5ee1db9d17817b70cb", "favoriteGenre": "Animation"},
        {"userId": "69bde9c6c661ee886a15e702", "favoriteGenre": "Children"},
    ]

    created = client.post("/recommendations/room/poll", json=payload)
    assert created.status_code == 200

    poll = created.json()
    assert len(poll["options"]) == 3
    assert poll["options"][0]["consensus_score"] >= poll["options"][1]["consensus_score"] >= poll["options"][2]["consensus_score"]

    top_movie = poll["options"][0]["movieId"]
    second_movie = poll["options"][1]["movieId"]

    vote_1 = client.post(f"/recommendations/room/poll/{poll['pollId']}/vote", json={"userId": "u1", "movieId": top_movie})
    vote_2 = client.post(f"/recommendations/room/poll/{poll['pollId']}/vote", json={"userId": "u2", "movieId": top_movie})
    vote_3 = client.post(f"/recommendations/room/poll/{poll['pollId']}/vote", json={"userId": "u3", "movieId": second_movie})

    assert vote_1.status_code == 200
    assert vote_2.status_code == 200
    assert vote_3.status_code == 200

    final_poll = vote_3.json()
    assert final_poll["votesCast"] == 3
    assert final_poll["winner"]["movieId"] == top_movie
    assert final_poll["winner"]["voteCount"] == 2


def test_room_poll_allows_user_to_change_vote(client: TestClient) -> None:
    payload = [
        {"userId": "69bb3d5ee1db9d17817b70cb", "favoriteGenre": "Animation"},
        {"userId": "69bde9c6c661ee886a15e702", "favoriteGenre": "Children"},
    ]

    created = client.post("/recommendations/room/poll", json=payload)
    poll = created.json()
    first_movie = poll["options"][0]["movieId"]
    second_movie = poll["options"][1]["movieId"]

    first_vote = client.post(f"/recommendations/room/poll/{poll['pollId']}/vote", json={"userId": "u1", "movieId": second_movie})
    second_vote = client.post(f"/recommendations/room/poll/{poll['pollId']}/vote", json={"userId": "u1", "movieId": first_movie})

    assert first_vote.status_code == 200
    assert second_vote.status_code == 200

    updated = second_vote.json()
    assert updated["votesCast"] == 1
    assert updated["winner"]["movieId"] == first_movie


def test_room_poll_tie_breaks_by_consensus_score(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_room_recommendations(_: Any) -> dict[str, Any]:
        return {
            "success": True,
            "totalUsers": 2,
            "recommendationCount": 3,
            "recommendations": [
                {"movieId": 10, "title": "Alpha", "genres": ["Action"], "consensus_score": 0.95, "reasons": ["A"]},
                {"movieId": 20, "title": "Beta", "genres": ["Animation"], "consensus_score": 0.90, "reasons": ["B"]},
                {"movieId": 30, "title": "Gamma", "genres": ["Children"], "consensus_score": 0.80, "reasons": ["C"]},
            ],
        }

    monkeypatch.setattr(main.service, "_recommend_room_from_request", fake_room_recommendations)

    created = client.post(
        "/recommendations/room/poll",
        json=[
            {"userId": "u1", "favoriteGenre": "Action"},
            {"userId": "u2", "favoriteGenre": "Animation"},
        ],
    )

    poll = created.json()
    vote_1 = client.post(f"/recommendations/room/poll/{poll['pollId']}/vote", json={"userId": "u1", "movieId": 20})
    vote_2 = client.post(f"/recommendations/room/poll/{poll['pollId']}/vote", json={"userId": "u2", "movieId": 30})

    assert vote_1.status_code == 200
    assert vote_2.status_code == 200

    final_poll = vote_2.json()
    assert final_poll["winner"]["movieId"] == 20
    assert final_poll["winner"]["voteCount"] == 1
    assert final_poll["winner"]["consensus_score"] == 0.9


