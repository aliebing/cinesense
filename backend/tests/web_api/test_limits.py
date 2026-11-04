from cinesense.web_api.deps import get_limiter
from cinesense.web_api.limits import SITE_DAY, VISITOR_DAY, VISITOR_MINUTE, TurnLimiter, visitor_of
from tests.web_api.test_chat import chat_client, events, fake_runner


class Clock:
    def __init__(self, t: float = 1_800_000_000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t


def limiter(clock, minute=3, day=5, site=8):
    return TurnLimiter(per_visitor_minute=minute, per_visitor_day=day, site_day=site, clock=clock)


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


def test_inspect_counts_against_the_same_limit():
    client = limited_client(limiter(Clock(), minute=1))
    body = {"thread_id": "t1", "message": "hi"}
    client.post("/api/chat", json=body)
    res = client.post("/api/inspect", json=body)
    assert res.status_code == 429
    assert res.json()["detail"] == VISITOR_MINUTE
