from fastapi.testclient import TestClient

from cinesense.core.config import get_settings
from cinesense.web_api.deps import get_limiter, get_tech_limiter
from cinesense.web_api.limits import (
    SITE_DAY,
    VISITOR_DAY,
    VISITOR_MINUTE,
    MemoryTurnStore,
    TurnLimiter,
    visitor_of,
)
from tests.web_api.test_chat import chat_client, events, fake_runner
from tests.web_api.test_inspect import make_app
from tests.web_api.test_inspect import runner as inspect_runner


class Clock:
    def __init__(self, t: float = 1_800_000_000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t


def limiter(clock, minute=3, day=5, site=8, store=None, scope="chat"):
    return TurnLimiter(
        per_visitor_minute=minute, per_visitor_day=day, site_day=site, clock=clock, store=store, scope=scope
    )


def test_allows_turns_under_every_limit():
    lim = limiter(Clock())
    assert [lim.check("a") for _ in range(3)] == [None, None, None]


def test_per_minute_limit_then_free_again_after_a_minute():
    clock = Clock()
    lim = limiter(clock)
    for _ in range(3):
        lim.check("a")
    assert lim.check("a") == VISITOR_MINUTE
    clock.t += 61
    assert lim.check("a") is None


def test_per_visitor_daily_limit_and_other_visitors_unaffected():
    clock = Clock()
    lim = limiter(clock)
    for _ in range(5):
        assert lim.check("a") is None
        clock.t += 30
    assert lim.check("a") == VISITOR_DAY
    assert lim.check("b") is None


def test_site_wide_daily_limit():
    clock = Clock()
    lim = limiter(clock)
    for i in range(8):
        assert lim.check(f"v{i}") is None
    assert lim.check("new") == SITE_DAY


def test_limits_reset_on_the_next_day():
    clock = Clock()
    lim = limiter(clock)
    for i in range(8):
        lim.check(f"v{i}")
    clock.t += 86_400
    assert lim.check("new") is None


def test_refused_turns_do_not_count():
    clock = Clock()
    lim = limiter(clock, minute=1)
    lim.check("a")
    for _ in range(10):
        lim.check("a")
    clock.t += 61
    assert lim.check("a") is None  # 2 counted turns, not 11: still under the daily 5


def test_daily_counts_survive_a_restart():
    """The daily counters live in the store (Postgres in production), so a new process starts from them."""
    clock, store = Clock(), MemoryTurnStore()
    first = limiter(clock, store=store)
    for _ in range(5):
        first.check("a")
        clock.t += 30
    restarted = limiter(clock, store=store)
    assert restarted.check("a") == VISITOR_DAY


def test_site_count_survives_a_restart():
    clock, store = Clock(), MemoryTurnStore()
    first = limiter(clock, store=store)
    for i in range(8):
        first.check(f"v{i}")
    assert limiter(clock, store=store).check("new") == SITE_DAY


def test_chat_and_technical_view_count_separately_in_one_store():
    clock, store = Clock(), MemoryTurnStore()
    chat = limiter(clock, day=1, store=store, scope="chat")
    tech = limiter(clock, day=1, store=store, scope="tech")
    assert chat.check("a") is None
    assert tech.check("a") is None
    assert chat.check("a") == VISITOR_DAY


class BrokenStore:
    def counts(self, day, scope, visitor):
        raise RuntimeError("database down")

    def add(self, day, scope, visitor):
        raise RuntimeError("database down")


def test_a_failing_store_falls_back_to_counting_in_memory():
    lim = limiter(Clock(), minute=10, day=2, store=BrokenStore())
    assert [lim.check("a") for _ in range(3)] == [None, None, VISITOR_DAY]


def test_visitor_is_the_address_the_proxy_added_last():
    assert visitor_of({"x-forwarded-for": "6.6.6.6, 203.0.113.9"}, "172.19.0.2") == "203.0.113.9"
    assert visitor_of({}, "198.51.100.4") == "198.51.100.4"


def limited_client(lim):
    client = chat_client(fake_runner)
    client.app.dependency_overrides[get_limiter] = lambda: lim
    return client


def test_chat_over_the_limit_answers_with_a_friendly_error_event():
    client = limited_client(limiter(Clock(), minute=1))
    body = {"thread_id": "t1", "message": "hi"}
    assert events(client.post("/api/chat", json=body).text)[-1][0] == "final"
    last = events(client.post("/api/chat", json=body).text)[-1]
    assert last == ("error", {"text": VISITOR_MINUTE})


def test_inspect_has_its_own_limit():
    client = limited_client(limiter(Clock(), minute=1))
    client.post("/api/chat", json={"thread_id": "t1", "message": "hi"})  # the chat's limit is used up …
    tech = TestClient(make_app(inspect_runner))
    tech.app.dependency_overrides[get_limiter] = client.app.dependency_overrides[get_limiter]
    tech_lim = limiter(Clock(), minute=1)
    tech.app.dependency_overrides[get_tech_limiter] = lambda: tech_lim
    body = {"thread_id": "t1", "message": "hi"}
    assert tech.post("/api/inspect", json=body).status_code == 200  # … the technical view still runs
    res = tech.post("/api/inspect", json=body)
    assert res.status_code == 429
    assert res.json()["detail"] == VISITOR_MINUTE


def test_default_daily_limits_25_for_the_chat_and_50_for_the_technical_view(monkeypatch):
    for name in ("CHAT_LIMIT_PER_DAY", "TECH_LIMIT_PER_DAY"):
        monkeypatch.delenv(name, raising=False)
    assert get_limiter().per_visitor_day == 25
    assert get_tech_limiter().per_visitor_day == 50
    assert get_settings().chat_per_day == 25
