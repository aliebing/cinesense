"""A mood search keeps only the best TAG_LIMIT films: its total is then a lower bound ("500+"), not a count."""

from cinesense.core.criteria import SearchCriteria
from cinesense.data_sources.fixture import FixtureProvider
from cinesense.search import service
from cinesense.search.service import SearchService


def test_a_tag_search_at_the_limit_says_its_total_is_capped(monkeypatch):
    p = FixtureProvider()
    c = SearchCriteria(tags=[{"idx": 0, "weight": 6, "mode": "prefer"}])
    assert SearchService(p).run(c).total_capped is False
    monkeypatch.setattr(service, "TAG_LIMIT", 5)
    res = SearchService(p).run(c)
    assert res.total <= 5 and res.total_capped is True


def test_searches_without_mood_tags_are_never_capped():
    assert SearchService(FixtureProvider()).run(SearchCriteria()).total_capped is False


def test_the_api_passes_it_on():
    from fastapi.testclient import TestClient

    from tests.web_api.test_api import make_app

    assert "total_capped" in TestClient(make_app()).post("/api/search", json={}).json()
