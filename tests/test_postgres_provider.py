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
    assert hits and any(m.id == "ml-2571" for m, _, _ in hits)
    assert all(isinstance(chunk, str) and chunk for _, _, chunk in hits)
