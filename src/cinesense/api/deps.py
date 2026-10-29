from cinesense.providers.base import MovieProvider
from cinesense.providers.fixture import FixtureProvider

_provider: MovieProvider = FixtureProvider()


def get_provider() -> MovieProvider:
    """FastAPI dependency; later plans swap in the TMDB-backed provider here."""
    return _provider
