"""A mood search keeps its TAG_LIMIT best films after the hard filters and exclusions, not before: "horror + funny,
from 2003" ranks the best films from 2003, not the films from 2003 among the best of all years."""

from types import SimpleNamespace

import pytest

from cinesense.core.criteria import SearchCriteria
from cinesense.data_sources.fixture import FixtureProvider
from cinesense.search import service
from cinesense.search.service import SearchService

LIMIT = 5
TAG = {"idx": 0, "weight": 6, "mode": "prefer"}


@pytest.fixture(autouse=True)
def small_cap(monkeypatch):
    monkeypatch.setattr(service, "TAG_LIMIT", LIMIT)


def _tag_order(p) -> list[str]:
    return [i for i, _ in p.tag_search({0: 6}, [], [], limit=1000)[0]]


def test_a_filter_still_fills_the_cap():
    p = FixtureProvider()
    c = SearchCriteria(tags=[TAG], year_from=2000)
    res = SearchService(p).run(c, 0, 50)
    assert len([m for m in p.list_movies() if m.year and m.year >= 2000]) > LIMIT
    assert res.total == LIMIT and res.total_capped is True
    assert all(r.movie.year >= 2000 for r in res.items)
    by_id = {m.id: m for m in p.list_movies()}
    best = [i for i in _tag_order(p) if (by_id[i].year or 0) >= 2000][:LIMIT]
    assert {r.movie.id for r in res.items} == set(best)


def test_an_excluded_genre_still_fills_the_cap_and_counts_what_it_hid():
    p = FixtureProvider()
    c = SearchCriteria(tags=[TAG], exclude_genres=["Action"])
    res = SearchService(p).run(c, 0, 50)
    assert res.total == LIMIT
    assert not any("Action" in r.movie.genres for r in res.items)
    # hidden here: the Action films that rank above the last film kept
    by_id = {m.id: m for m in p.list_movies()}
    order = _tag_order(p)
    kept = [i for i in order if "Action" not in by_id[i].genres][:LIMIT]
    above = order[: order.index(kept[-1])]
    assert res.hidden_by["genre:Action"] == sum("Action" in by_id[i].genres for i in above) > 0


def test_disliked_films_still_fill_the_cap():
    p = FixtureProvider()
    disliked = _tag_order(p)[:2]
    profile = SimpleNamespace(disliked=disliked, liked=[], taste={})
    res = SearchService(p).run(SearchCriteria(tags=[TAG]), 0, 50, profile)
    assert res.total == LIMIT
    assert not {r.movie.id for r in res.items} & set(disliked)
