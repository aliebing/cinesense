import pytest

pytestmark = pytest.mark.db


@pytest.fixture
def provider(db_url):
    from cinesense.data_sources.db import connect
    from cinesense.data_sources.postgres import PostgresProvider

    return PostgresProvider(lambda: connect(db_url))


def test_get_movie_matrix(provider):
    m = provider.get_movie("ml-2571")
    assert m.title == "The Matrix" and m.imdb_id == "tt0133093" and "scifi" in m.world_ids


def test_list_tags_and_vectors(provider):
    tags = provider.list_tags()
    assert len(tags) == 1128
    v = provider.tag_vectors(["ml-2571"])
    assert v.shape == (1, 1128)


def test_semantic_search_returns_chunks(provider):
    import asyncio

    from cinesense.core.config import get_settings
    from cinesense.data_sources.embeddings import EmbeddingClient

    vec = asyncio.run(
        EmbeddingClient(get_settings().openrouter_api_key).embed(["hackers discover reality is a simulation"])
    )[0]
    hits = provider.semantic_search(vec, k=10)
    titles = [m.title for m, _, _ in hits]
    assert len(hits) == 10  # ef_search raised: recall is no longer capped
    assert any("Matrix" in t or t in ("eXistenZ", "The Thirteenth Floor") for t in titles)
    assert all(isinstance(chunk, str) and chunk for _, _, chunk in hits)


def test_feedback_store_roundtrip_and_profile(provider, db_url):
    import uuid

    from cinesense.data_sources.db import connect
    from cinesense.taste.feedback import PostgresFeedbackStore
    from cinesense.taste.profile import build_profile

    store, user = PostgresFeedbackStore(lambda: connect(db_url)), f"test-{uuid.uuid4()}"
    try:
        store.set(user, "ml-2571", 1)
        store.set(user, "ml-1721", -1)
        assert store.get(user) == {"ml-2571": 1, "ml-1721": -1}
        prof = build_profile(store.get(user), provider)
        assert "cyberpunk" in prof.taste_names and provider.mean_tag_vector().shape == (1128,)
    finally:
        store.clear(user)
    assert store.get(user) == {}


def test_title_search_treats_wildcards_literally(provider):
    assert len(provider.search_title("%")) < 50
    assert len(provider.search_title("_")) < 50


def test_title_search_ranks_titles_containing_the_query_above_sound_alikes(provider):
    s = provider.search_title("Matrix")
    assert s["ml-2571"] >= 0.85  # "The Matrix" contains the query
    sound_alikes = [v for k, v in provider.search_title("Revenant").items() if k not in ("ml-139385", "ml-91947")]
    assert all(v < provider.search_title("Revenant")["ml-139385"] for v in sound_alikes)


def test_title_search_matches_the_german_title_of_live_imports(provider):
    """Needs the Winnetou backfill (python -m cinesense.catalog_import.pipeline --no-films --no-plots --enrich-live)."""
    assert provider.search_title("Winnetou").get("imdb-tt0057687", 0) >= 0.85  # Apache Gold = Winnetou 1. Teil
    assert provider.get_movie("imdb-tt0057687").title_de
