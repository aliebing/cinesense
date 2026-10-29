import json

from fastapi.testclient import TestClient

from cinesense.api.app import create_app
from cinesense.api.deps import get_agent, get_embedder, get_live, get_provider, get_streaming, get_trailers
from cinesense.providers.fixture import FixtureProvider


def make_app():
    app = create_app(load_env=False)
    app.dependency_overrides[get_provider] = FixtureProvider
    for dep in (get_streaming, get_embedder, get_live, get_trailers):
        app.dependency_overrides[dep] = lambda: None
    return app


def events(text: str) -> list[tuple[str, dict]]:
    out = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        out.append((lines["event"], json.loads(lines["data"])))
    return out


def fake_runner(thread_id, message, criteria, on_status=None):
    on_status("Setting mood tags…")
    return {
        "reply": f"echo {message}",
        "criteria": criteria,
        "results": [],
        "proposals": [],
        "handoff": None,
        "usage": {"input_tokens": 1, "output_tokens": 2},
    }


def chat_client(runner):
    app = make_app()
    app.dependency_overrides[get_agent] = lambda: runner
    return TestClient(app)


BODY = {"thread_id": "abc", "message": "dark space films", "criteria": {}}


def test_chat_streams_status_and_final():
    r = chat_client(fake_runner).post("/api/chat", json=BODY)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    ev = events(r.text)
    assert ev[0] == ("status", {"text": "Setting mood tags…"})
    assert ev[-1][0] == "final" and ev[-1][1]["reply"] == "echo dark space films"


def test_chat_error_event_without_llm():
    ev = events(chat_client(None).post("/api/chat", json=BODY).text)
    assert ev == [
        ("error", {"text": "The assistant is unavailable right now — you can still use the chips and search."})
    ]


def test_chat_error_event_when_runner_fails():
    def broken(*a, **k):
        raise RuntimeError("upstream 500")

    ev = events(chat_client(broken).post("/api/chat", json=BODY).text)
    assert ev[-1][0] == "error" and "upstream" not in ev[-1][1]["text"]


def test_chat_validates_message_length():
    c = chat_client(fake_runner)
    assert c.post("/api/chat", json={**BODY, "message": ""}).status_code == 422
    assert c.post("/api/chat", json={**BODY, "message": "x" * 1001}).status_code == 422
