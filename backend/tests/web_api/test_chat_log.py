"""The visitor log (/admin/visitors): one entry per agent turn, hashed visitor and thread, kept 30 days."""

import datetime as dt

from fastapi.testclient import TestClient

from cinesense.web_api.chat_log import MemoryChatLog, entry_from_turn, keyed_hash, log_turn
from cinesense.web_api.deps import get_chat_log
from tests.web_api.test_chat import chat_client, fake_runner
from tests.web_api.test_inspect import make_app as inspect_app
from tests.web_api.test_inspect import runner as inspect_runner


def turn(**kw):
    out = {
        "reply": "Try Alien.",
        "criteria": {},
        "results": [{"movie": {"title": "Alien", "year": 1979}, "match_percent": 90}],
        "tool_trace": [{"name": "set_mood_tags", "args": {"tags": ["dark"]}, "result": "long text"}],
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }
    return entry_from_turn(out, scope="chat", visitor="v1", thread="t1", message="dark", cost_usd=0.01, **kw)


def test_page_lists_newest_first_with_sums_and_scope():
    log = MemoryChatLog()
    log.write(turn(duration_ms=1000))
    log.write({**turn(duration_ms=3000), "scope": "tech", "message": "tech question"})
    page = log.page(None, 0, 50)
    assert [e["message"] for e in page["items"]] == ["tech question", "dark"]
    assert page["items"][1]["films"] == 1 and page["items"][1]["tools"] == ["set_mood_tags"]
    assert page["sums"] == {"count": 2, "cost_usd": 0.02, "avg_duration_ms": 2000, "visitors": 1}
    assert log.page("chat", 0, 50)["total"] == 1


def test_detail_has_the_earlier_messages_of_the_conversation():
    log = MemoryChatLog()
    log.write({**turn(), "message": "first"})
    log.write({**turn(), "thread": "other", "message": "elsewhere"})
    log.write({**turn(), "message": "second"})
    d = log.detail(3)
    assert d["reply"] == "Try Alien." and d["films"][0] == {"title": "Alien", "year": 1979, "match": 90}
    assert [c["message"] for c in d["conversation"]] == ["first"]
    assert log.detail(99) is None


def test_entries_older_than_the_retention_are_dropped():
    log = MemoryChatLog(days=30)
    log.write({**turn(), "ts": dt.datetime.now(dt.UTC) - dt.timedelta(days=31), "message": "old"})
    log.write(turn())
    assert [e["message"] for e in log.page(None, 0, 50)["items"]] == ["dark"]


def test_log_turn_hashes_visitor_and_thread_and_never_raises():
    log = MemoryChatLog()
    log_turn(
        log,
        scope="chat",
        visitor="203.0.113.9",
        thread_id="abc",
        message="hi",
        out=None,
        duration_s=0.5,
        error="TimeoutError",
        secret="s",
        model="anthropic/claude-haiku-5.5",
        tag_names=[],
    )
    e = log.detail(1)
    assert e["visitor"] == keyed_hash("s", "203.0.113.9") and "203.0.113" not in e["visitor"]
    assert e["thread"] == keyed_hash("s", "abc") and e["error"] == "TimeoutError" and e["duration_ms"] == 500

    class Broken:
        def write(self, entry):
            raise OSError("disk full")

    log_turn(
        Broken(),
        scope="chat",
        visitor="x",
        thread_id="t",
        message="hi",
        out=None,
        duration_s=0,
        error=None,
        secret="s",
        model="m",
        tag_names=[],
    )  # no exception


def test_a_chat_turn_is_logged():
    client = chat_client(fake_runner)
    log = MemoryChatLog()
    client.app.dependency_overrides[get_chat_log] = lambda: log
    client.post("/api/chat", json={"thread_id": "t1", "message": "something dark"})
    items = log.page(None, 0, 10)["items"]
    assert len(items) == 1 and items[0]["message"] == "something dark" and items[0]["scope"] == "chat"
    assert items[0]["input_tokens"] == 1 and items[0]["output_tokens"] == 2


def test_a_tech_turn_is_logged_as_tech(monkeypatch):
    monkeypatch.delenv("TECH_USER", raising=False)
    monkeypatch.delenv("TECH_PASSWORD", raising=False)
    app = inspect_app(inspect_runner)
    log = MemoryChatLog()
    app.dependency_overrides[get_chat_log] = lambda: log
    TestClient(app).post("/api/inspect", json={"thread_id": "t", "message": "dark"})
    (item,) = log.page(None, 0, 10)["items"]
    assert item["scope"] == "tech" and item["tools"] == ["set_mood_tags"]


def test_admin_endpoints_need_the_login_and_show_the_log(monkeypatch):
    monkeypatch.setenv("TECH_USER", "admin")
    monkeypatch.setenv("TECH_PASSWORD", "s3cret")
    app = inspect_app(inspect_runner)
    log = MemoryChatLog()
    log.write(turn())
    app.dependency_overrides[get_chat_log] = lambda: log
    client = TestClient(app)
    assert client.get("/api/admin/visitors").status_code == 401
    client.post("/api/admin/login", json={"name": "admin", "password": "s3cret"})
    page = client.get("/api/admin/visitors").json()
    assert page["total"] == 1 and page["items"][0]["message"] == "dark"
    assert client.get("/api/admin/visitors/1").json()["reply"] == "Try Alien."
    assert client.get("/api/admin/visitors/9").status_code == 404
    assert client.get("/api/admin/visitors?scope=nope").status_code == 422
