"""POST /api/inspect: one agent turn with everything a reviewer wants to see, as plain JSON (no images)."""

from fastapi.testclient import TestClient

from cinesense.data_sources.fixture import FixtureProvider
from cinesense.web_api.app import create_app
from cinesense.web_api.deps import (
    get_agent,
    get_embedder,
    get_live,
    get_provider,
    get_streaming,
    get_trailer_checker,
    get_trailers,
)


def make_app(runner):
    app = create_app(load_env=False)
    app.dependency_overrides[get_provider] = FixtureProvider
    for dep in (get_streaming, get_embedder, get_live, get_trailers, get_trailer_checker):
        app.dependency_overrides[dep] = lambda: None
    app.dependency_overrides[get_agent] = lambda: runner
    return app


def runner(thread_id, message, criteria, on_status=None, profile=None):
    film = FixtureProvider().list_movies()[0]
    return {
        "reply": "Here is why.",
        "criteria": {**criteria, "tags": [{"idx": 0, "weight": 7, "mode": "prefer"}]},
        "results": [
            {"movie": film.model_dump(mode="json"), "match_percent": 91, "reasons": ["dark 90%"], "score": 0.9}
        ],
        "picks": 1,
        "usage": {"input_tokens": 1_000_000, "output_tokens": 0},
        "tool_trace": [{"name": "set_mood_tags", "args": {"tags": ["dark"]}, "result": "ok"}],
        "prompts": {"agent": "You are CineSense…", "explain": "You explain…", "explain_input": "Wish: …"},
        "rounds": 1,
        "grounding_fallback": False,
        "grounding_reason": [],
    }


def test_inspect_returns_the_whole_turn_as_text():
    r = TestClient(make_app(runner)).post("/api/inspect", json={"thread_id": "t1", "message": "something dark"})
    assert r.status_code == 200
    d = r.json()
    assert d["reply"] == "Here is why."
    assert d["results"][0]["match_percent"] == 91 and "poster_url" not in d["results"][0]  # text only
    assert d["picks"] == 1
    assert d["tools"][0]["name"] == "set_mood_tags"
    assert d["prompts"]["agent"].startswith("You are")
    assert d["tags"][0]["tag"] and d["tags"][0]["weight"] == 7
    assert "criteria_summary" in d and d["usage"]["input_tokens"] == 1_000_000
    assert d["cost_usd"] >= 0 and d["latency_s"] >= 0 and d["model"]
    film = FixtureProvider().list_movies()[0]
    assert d["results"][0]["imdb_id"] == film.imdb_id  # the reviewer's list links each title to IMDb


def test_inspect_without_an_llm_key_says_so():
    r = TestClient(make_app(None)).post("/api/inspect", json={"thread_id": "t1", "message": "x"})
    assert r.status_code == 503


def test_inspect_needs_the_tech_login_when_one_is_configured(monkeypatch):
    monkeypatch.setenv("TECH_USER", "admin")
    monkeypatch.setenv("TECH_PASSWORD", "s3cret")
    client = TestClient(make_app(runner))
    body = {"thread_id": "t1", "message": "hi"}
    r = client.post("/api/inspect", json=body)
    assert r.status_code == 401
    assert r.headers["www-authenticate"].startswith("Basic")
    assert client.post("/api/inspect", json=body, auth=("admin", "wrong")).status_code == 401
    assert client.post("/api/inspect", json=body, auth=("admin", "s3cret")).status_code == 200


def test_inspect_is_open_without_a_configured_login(monkeypatch):
    monkeypatch.delenv("TECH_USER", raising=False)
    monkeypatch.delenv("TECH_PASSWORD", raising=False)
    assert (
        TestClient(make_app(runner)).post("/api/inspect", json={"thread_id": "t1", "message": "hi"}).status_code == 200
    )
