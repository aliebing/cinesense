"""Widening against the real catalogue: a mood tag with 'In cinemas' finds nothing (cinema films have no
Tag Genome data), and the plot-search option must find cinema films."""

import pytest

pytestmark = pytest.mark.db


@pytest.fixture
def provider(db_url):
    from cinesense.data_sources.db import connect
    from cinesense.data_sources.postgres import PostgresProvider

    return PostgresProvider(lambda: connect(db_url))


@pytest.fixture
def service(provider):
    from cinesense.core.config import get_settings
    from cinesense.data_sources.embeddings import EmbeddingClient
    from cinesense.search.service import SearchService

    return SearchService(provider, None, EmbeddingClient(get_settings().openrouter_api_key))


def test_cinema_plus_mood_tag_has_a_way_out(provider, service):
    from cinesense.core.criteria import SearchCriteria, TagCriterion
    from cinesense.search.widening import probe

    tags = provider.list_tags()
    c = SearchCriteria(tags=[TagCriterion(idx=tags.index("funny"))], availability="cinema")
    opts = {o.id: o for o in probe(service, c, tags, current=service.count(c))}
    assert opts["tags-to-plot"].count > 0
    hits = service.run(opts["tags-to-plot"].criteria, 0, 5).items
    assert hits and all(r.movie.availability.in_cinema_de for r in hits)


def test_semantic_search_only_ids(provider, service):
    cinema = [m.id for m in provider.list_movies() if m.availability.in_cinema_de]
    hits = provider.semantic_search(service._embed("a family comedy"), k=10, only_ids=cinema)
    assert hits and {m.id for m, _, _ in hits} <= set(cinema)


def test_cinema_mood_with_no_horror_still_has_a_way_out(provider, service):
    from cinesense.core.criteria import SearchCriteria, TagCriterion
    from cinesense.search.widening import probe

    tags = provider.list_tags()
    c = SearchCriteria(
        tags=[TagCriterion(idx=tags.index("funny")), TagCriterion(idx=tags.index("horror"), mode="not")],
        exclude_genres=["Horror"],
        availability="cinema",
    )
    opts = {o.id: o for o in probe(service, c, tags, current=service.count(c))}
    assert 0 < opts["tags-to-plot"].count <= 31
