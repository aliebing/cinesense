from fastapi.testclient import TestClient

from cinesense.api.app import create_app
from cinesense.api.deps import (
    get_agent,
    get_embedder,
    get_feedback_store,
    get_live,
    get_provider,
    get_streaming,
    get_trailer_checker,
    get_trailers,
)
from cinesense.personal.feedback import MemoryFeedbackStore
from cinesense.providers.fixture import FixtureProvider

USER = {"X-CineSense-User": "0b6f7c1e-2c55-4c4e-9a0b-4d1f3f1a2b3c"}
PROVIDER = FixtureProvider()


def client(runner=None):
    app = create_app(load_env=False)
    store = MemoryFeedbackStore()
    app.dependency_overrides[get_provider] = lambda: PROVIDER
    app.dependency_overrides[get_feedback_store] = lambda: store
    app.dependency_overrides[get_agent] = lambda: runner
    for dep in (get_streaming, get_embedder, get_live, get_trailers, get_trailer_checker):
        app.dependency_overrides[dep] = lambda: None
    return TestClient(app)


def fid(title):
    return next(m.id for m in PROVIDER.list_movies() if m.title == title)


def test_feedback_roundtrip_and_reset():
    c = client()
    r = c.post("/api/feedback", json={"film_id": fid("The Matrix"), "value": 1}, headers=USER)
    assert r.status_code == 200 and "cyberpunk" in r.json()["taste"]
    c.post("/api/feedback", json={"film_id": fid("Titanic"), "value": -1}, headers=USER)
    prof = c.get("/api/profile", headers=USER).json()
    assert [f["title"] for f in prof["liked"]] == ["The Matrix"] and prof["disliked"][0]["title"] == "Titanic"
    assert c.delete("/api/profile", headers=USER).json() == {"liked": [], "disliked": [], "taste": []}
    assert c.get("/api/profile", headers=USER).json()["liked"] == []


def test_toggle_removes_like():
    c = client()
    c.post("/api/feedback", json={"film_id": fid("The Matrix"), "value": 1}, headers=USER)
    c.post("/api/feedback", json={"film_id": fid("The Matrix"), "value": 0}, headers=USER)
    assert c.get("/api/profile", headers=USER).json()["liked"] == []


def test_invalid_user_header_ignored():
    c = client()
    bad = {"X-CineSense-User": "x' or 1=1"}
    assert c.post("/api/feedback", json={"film_id": "ml-1", "value": 1}, headers=bad).status_code == 400
    assert c.get("/api/profile", headers=bad).json() == {"liked": [], "disliked": [], "taste": []}
    assert c.post("/api/discover", json={"criteria": {}}, headers=bad).status_code == 200


def test_feedback_validates_value():
    assert client().post("/api/feedback", json={"film_id": "ml-1", "value": 5}, headers=USER).status_code == 422


def test_discover_and_related_hide_disliked():
    c = client()
    titanic = fid("Titanic")
    c.post("/api/feedback", json={"film_id": titanic, "value": -1}, headers=USER)
    ids = [
        r["movie"]["id"]
        for r in c.post("/api/discover", json={"criteria": {}, "limit": 50}, headers=USER).json()["items"]
    ]
    assert titanic not in ids
    other = next(
        m
        for m in PROVIDER.list_movies()
        if m.id != titanic and set(m.world_ids) & set(PROVIDER.get_movie(titanic).world_ids)
    )
    world = (set(other.world_ids) & set(PROVIDER.get_movie(titanic).world_ids)).pop()
    rel = c.get(f"/api/movies/{other.id}/related?world_id={world}&limit=100", headers=USER).json()
    assert titanic not in [r["movie"]["id"] for r in rel]


def test_chat_receives_profile():
    seen = {}

    def runner(thread_id, message, criteria, on_status=None, profile=None):
        seen["profile"] = profile
        return {"reply": "ok", "criteria": criteria, "results": [], "proposals": [], "handoff": None, "usage": {}}

    c = client(runner)
    c.post("/api/feedback", json={"film_id": fid("The Matrix"), "value": 1}, headers=USER)
    c.post("/api/chat", json={"thread_id": "t", "message": "hi", "criteria": {}}, headers=USER)
    assert seen["profile"] is not None and seen["profile"].liked == [fid("The Matrix")]
