import pytest

from cinesense.web_api.chat_log import PostgresChatLog, entry_from_turn

pytestmark = pytest.mark.db

MARK = "pytest-visitor-log"  # the scope of this test's rows; removed afterwards


@pytest.fixture
def store(db_url):
    from cinesense.data_sources.db import connect

    s = PostgresChatLog(lambda: connect(db_url))
    yield s
    with connect(db_url) as c:
        c.execute("delete from chat_log where scope = %s", (MARK,))
        c.commit()


def test_writes_lists_and_shows_a_turn_with_its_conversation(store):
    out = {"reply": "Try Alien.", "results": [{"movie": {"title": "Alien", "year": 1979}}], "tool_trace": []}
    for msg in ("first", "second"):
        store.write(entry_from_turn(out, scope=MARK, visitor="v", thread="t-db", message=msg, cost_usd=0.001))
    page = store.page(MARK, 0, 10)
    assert [e["message"] for e in page["items"]] == ["second", "first"] and page["sums"]["count"] == 2
    d = store.detail(page["items"][0]["id"])
    assert d["films"] == [{"title": "Alien", "year": 1979, "match": None}]
    assert [c["message"] for c in d["conversation"]] == ["first"]
