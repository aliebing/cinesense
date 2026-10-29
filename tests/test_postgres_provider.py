import pytest

pytestmark = pytest.mark.db


@pytest.fixture
def provider(db_url):
    from cinesense.db import connect
    from cinesense.providers.postgres import PostgresProvider

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

    from cinesense.config import get_settings
    from cinesense.ingest.embeddings import EmbeddingClient

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

    from cinesense.db import connect
    from cinesense.personal.feedback import PostgresFeedbackStore
    from cinesense.personal.profile import build_profile

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
