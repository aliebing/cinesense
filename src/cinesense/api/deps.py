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


@lru_cache
def get_trailers():
    s = get_settings()
    from cinesense.providers.youtube import MemoryTrailerStore, PostgresTrailerStore, YouTubeTrailerClient

    if s.database_url:
        from cinesense.db import connect

        store = PostgresTrailerStore(lambda: connect(s.database_url))
    else:
        store = MemoryTrailerStore()
    return YouTubeTrailerClient(s.youtube_api_key, store, daily_limit=s.youtube_daily_limit)


@lru_cache
def get_agent():
    """Chat runner (thread_id, message, criteria, on_status) -> dict, or None without an OpenRouter key."""
    s = get_settings()
    from cinesense.agent.llm import make_llm

    llm = make_llm(s)
    if llm is None:
        return None
    from langgraph.checkpoint.memory import MemorySaver

    from cinesense.agent.graph import build_graph, run_turn
    from cinesense.agent.tools import ToolKit, make_tools
    from cinesense.search.service import SearchService

    provider, streaming = get_provider(), get_streaming()
    service = SearchService(provider, streaming, get_embedder())
    graph = build_graph(
        llm,
        make_llm(s, max_tokens=1500),  # reasoning tokens count against the limit
        make_tools(ToolKit(service, provider, streaming)),
        service,
        provider,
        MemorySaver(),  # one process-wide memory; the client keeps the thread id
    )

    def runner(thread_id, message, criteria, on_status=None, profile=None):
        return run_turn(graph, thread_id, message, criteria, on_status, profile)

    return runner


@lru_cache
def get_feedback_store():
    s = get_settings()
    from cinesense.personal.feedback import MemoryFeedbackStore, PostgresFeedbackStore

    if s.database_url:
        from cinesense.db import connect

        return PostgresFeedbackStore(lambda: connect(s.database_url))
    return MemoryFeedbackStore()
