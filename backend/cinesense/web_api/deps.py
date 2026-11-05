"""Wiring: builds the data sources, the search service and the chat agent once per process from the settings."""

from functools import lru_cache

from cinesense.core.config import get_settings
from cinesense.data_sources.fixture import FixtureProvider


def _turn_store():
    """Daily turn counts in Postgres when configured (they survive a restart), otherwise in memory. The database
    URL is a server secret, so it keys the hash of the visitor addresses."""
    from cinesense.web_api.limits import MemoryTurnStore, PostgresTurnStore

    s = get_settings()
    if s.database_url:
        from cinesense.data_sources.db import connect

        return PostgresTurnStore(lambda: connect(s.database_url), secret=s.database_url)
    return MemoryTurnStore()


@lru_cache
def get_limiter():
    """One shared counter of agent turns per process (see limits.py). Tests override this."""
    from cinesense.web_api.limits import TurnLimiter

    s = get_settings()
    return TurnLimiter(s.chat_per_minute, s.chat_per_day, s.chat_site_per_day, store=_turn_store(), scope="chat")


@lru_cache
def get_tech_limiter():
    """The technical view's own counter: its turns don't use up the chat's daily limit, and it allows more."""
    from cinesense.web_api.limits import TurnLimiter

    s = get_settings()
    return TurnLimiter(s.chat_per_minute, s.tech_per_day, s.chat_site_per_day, store=_turn_store(), scope="tech")


@lru_cache
def get_provider():
    """Postgres catalogue when configured, otherwise the offline fixture. Tests override this."""
    s = get_settings()
    if s.database_url:
        from cinesense.data_sources.db import connect
        from cinesense.data_sources.postgres import PostgresProvider

        return PostgresProvider(lambda: connect(s.database_url))
    return FixtureProvider()


@lru_cache
def get_streaming():
    s = get_settings()
    if not s.streaming_api_key:
        return None
    from cinesense.data_sources.streaming import MemoryStreamingStore, PostgresStreamingStore, StreamingClient

    if s.database_url:
        from cinesense.data_sources.db import connect

        store = PostgresStreamingStore(lambda: connect(s.database_url))
    else:
        store = MemoryStreamingStore()
    return StreamingClient(s.streaming_api_key, store, monthly_limit=s.streaming_monthly_limit)


@lru_cache
def get_embedder():
    s = get_settings()
    if not s.openrouter_api_key:
        return None
    from cinesense.data_sources.embeddings import EmbeddingClient

    return EmbeddingClient(s.openrouter_api_key)


@lru_cache
def get_live():
    from cinesense.data_sources.live_search import LiveSearch

    return LiveSearch(get_streaming())


@lru_cache
def get_trailers():
    s = get_settings()
    from cinesense.data_sources.youtube import MemoryTrailerStore, PostgresTrailerStore, YouTubeTrailerClient

    if s.database_url:
        from cinesense.data_sources.db import connect

        store = PostgresTrailerStore(lambda: connect(s.database_url))
    else:
        store = MemoryTrailerStore()
    checker = get_trailer_checker()  # a search hit that cannot play here gives way to the next one
    return YouTubeTrailerClient(
        s.youtube_api_key, store, daily_limit=s.youtube_daily_limit, playable=checker.playable_ids
    )


def enrich_live_imports(ids: list[str], provider) -> None:
    """Films imported live get their German title, Wikipedia plot and embeddings; then the catalogue cache is
    reloaded so the next search sees them."""
    from cinesense.catalog_import.pipeline import enrich_new_films

    enrich_new_films(ids)
    if hasattr(provider, "refresh"):
        provider.refresh()


def agent_search_service():
    """The agent's search, the same as the results page's: titles outside the catalogue (e.g. "Winnetou") are
    looked up live (1 Streaming Availability call per new title, cached a day), imported lazily and enriched in a
    background thread, so the reply doesn't wait."""
    import threading

    from cinesense.search.service import SearchService

    provider = get_provider()

    def on_import(ids: list[str]) -> None:
        threading.Thread(
            target=enrich_live_imports, args=(ids, provider), name="enrich-live-imports", daemon=True
        ).start()

    return SearchService(provider, get_streaming(), get_embedder(), get_live(), on_import=on_import)


@lru_cache
def get_agent():
    """Chat runner (thread_id, message, criteria, on_status) -> dict, or None without an OpenRouter key."""
    s = get_settings()
    from cinesense.chat_agent.llm import make_llm

    llm = make_llm(s)
    if llm is None:
        return None
    from langgraph.checkpoint.memory import MemorySaver

    from cinesense.chat_agent.graph import build_graph, run_turn
    from cinesense.chat_agent.tools import ToolKit, make_tools

    provider, streaming = get_provider(), get_streaming()
    service = agent_search_service()
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
def get_chat_log():
    """The visitor log (chat_log.py): Postgres when configured, otherwise in memory. Tests override this."""
    s = get_settings()
    from cinesense.web_api.chat_log import MemoryChatLog, PostgresChatLog

    if s.database_url:
        from cinesense.data_sources.db import connect

        return PostgresChatLog(lambda: connect(s.database_url), days=s.chat_log_days)
    return MemoryChatLog(days=s.chat_log_days)


def log_secret() -> str:
    """Keys the visitor and conversation hashes of the log: a server secret, never stored with them."""
    s = get_settings()
    return s.database_url or s.tech_password or "cinesense-local"


@lru_cache
def get_feedback_store():
    s = get_settings()
    from cinesense.taste.feedback import MemoryFeedbackStore, PostgresFeedbackStore

    if s.database_url:
        from cinesense.data_sources.db import connect

        return PostgresFeedbackStore(lambda: connect(s.database_url))
    return MemoryFeedbackStore()


@lru_cache
def get_trailer_checker():
    s = get_settings()
    from cinesense.data_sources.trailer_check import TrailerChecker
    from cinesense.data_sources.youtube import MemoryTrailerStore, PostgresTrailerStore

    if s.database_url:
        from cinesense.data_sources.db import connect

        store = PostgresTrailerStore(lambda: connect(s.database_url))
    else:
        store = MemoryTrailerStore()
    return TrailerChecker(store, api_key=s.youtube_api_key, daily_api_calls=s.youtube_check_daily_calls)
