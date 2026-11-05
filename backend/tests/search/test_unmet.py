"""Wishes the top films do not show: named, so the chat says so instead of quietly meeting two of three."""

from cinesense.core.criteria import SearchCriteria, TagCriterion
from cinesense.data_sources.fixture import FixtureProvider
from cinesense.search.service import SearchService
from cinesense.search.widening import mood_coverage


def _tags(p, spec):
    return [TagCriterion(idx=p.list_tags().index(n), weight=w, mode=m) for n, w, m in spec]


def _top(p, c, n=3):
    return SearchService(p).run(c, 0, 5).items[:n]


def test_a_minor_wish_none_of_the_top_films_shows_is_missing():
    p = FixtureProvider()
    c = SearchCriteria(tags=_tags(p, [("funny", 8, "prefer"), ("scary", 2, "prefer")]))
    cov = mood_coverage(_top(p, c), c, p)
    assert cov.missing == ["scary"] and not cov.combined


def test_wishes_split_over_different_films_are_not_combined():
    p = FixtureProvider()
    c = SearchCriteria(tags=_tags(p, [("funny", 6, "prefer"), ("scary", 6, "prefer")]))
    cov = mood_coverage(_top(p, c), c, p)
    assert cov.missing == [] and not cov.combined  # comedies and thrillers, no film that is both


def test_met_wishes_and_not_tags_are_not_reported():
    p = FixtureProvider()
    c = SearchCriteria(tags=_tags(p, [("funny", 6, "prefer"), ("scary", 6, "not")]))
    cov = mood_coverage(_top(p, c), c, p)
    assert cov.missing == [] and cov.combined
    assert mood_coverage([], c, p).combined
