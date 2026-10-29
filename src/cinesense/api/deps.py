from functools import lru_cache

from cinesense.config import get_settings
from cinesense.providers.fixture import FixtureProvider


@lru_cache
def get_provider():
    """Postgres catalogue when configured, otherwise the offline fixture. Tests override this."""
    s = get_settings()
    if s.database_url:
        from cinesense.db import connect
        from cinesense.providers.postgres import PostgresProvider

        return PostgresProvider(lambda: connect(s.database_url))
    return FixtureProvider()


@lru_cache
def get_streaming():
    s = get_settings()
    if not s.streaming_api_key:
        return None
    from cinesense.providers.streaming import MemoryStreamingStore, PostgresStreamingStore, StreamingClient

    if s.database_url:
        from cinesense.db import connect

        store = PostgresStreamingStore(lambda: connect(s.database_url))
    else:
        store = MemoryStreamingStore()
    return StreamingClient(s.streaming_api_key, store, monthly_limit=s.streaming_monthly_limit)


@lru_cache
def get_embedder():
    s = get_settings()
    if not s.openrouter_api_key:
        return None
    from cinesense.ingest.embeddings import EmbeddingClient

    return EmbeddingClient(s.openrouter_api_key)


@lru_cache
def get_live():
    from cinesense.providers.live_search import LiveSearch

    return LiveSearch(get_streaming())
