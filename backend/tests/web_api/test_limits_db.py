import datetime as dt

import pytest

pytestmark = pytest.mark.db

DAY = dt.date(2001, 1, 1)  # a day no real traffic uses; its rows are removed afterwards


@pytest.fixture
def store(db_url):
    from cinesense.data_sources.db import connect, init_schema
    from cinesense.web_api.limits import PostgresTurnStore

    init_schema(db_url)
    s = PostgresTurnStore(lambda: connect(db_url), secret="test-secret")
    yield s
    with connect(db_url) as c:
        c.execute("delete from chat_turns where day <= %s", (DAY,))
        c.commit()


def test_counts_turns_per_visitor_and_for_the_site(store):
    store.add(DAY, "chat", "203.0.113.9")
    store.add(DAY, "chat", "203.0.113.9")
    store.add(DAY, "chat", "198.51.100.4")
    assert store.counts(DAY, "chat", "203.0.113.9") == (2, 3)
    assert store.counts(DAY, "tech", "203.0.113.9") == (0, 0)


def test_stores_no_plain_addresses(db_url, store):
    from cinesense.data_sources.db import connect

    store.add(DAY, "chat", "203.0.113.9")
    with connect(db_url) as c:
        visitors = [r[0] for r in c.execute("select visitor from chat_turns where day = %s", (DAY,)).fetchall()]
    assert "203.0.113.9" not in visitors and all("203.0.113" not in v for v in visitors)


def test_drops_earlier_days(db_url, store):
    from cinesense.data_sources.db import connect

    earlier = DAY - dt.timedelta(days=1)
    store.add(earlier, "chat", "a")
    store.add(DAY, "chat", "a")
    with connect(db_url) as c:
        left = c.execute("select count(*) from chat_turns where day = %s", (earlier,)).fetchone()[0]
    assert left == 0


def test_creates_its_table_when_missing(db_url):
    from cinesense.data_sources.db import connect
    from cinesense.web_api.limits import PostgresTurnStore

    with connect(db_url) as c:
        c.execute("drop table if exists chat_turns")
        c.commit()
    s = PostgresTurnStore(lambda: connect(db_url), secret="test-secret")
    assert s.counts(DAY, "chat", "a") == (0, 0)
