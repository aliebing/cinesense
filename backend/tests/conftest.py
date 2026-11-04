import pytest

from cinesense.core.models import Availability, Movie


@pytest.fixture(autouse=True)
def fresh_chat_limits():
    """Every test starts with untouched chat limits (the limiter is one shared counter per process)."""
    from cinesense.web_api.deps import get_limiter, get_tech_limiter

    get_limiter.cache_clear()
    get_tech_limiter.cache_clear()
    yield
    get_limiter.cache_clear()
    get_tech_limiter.cache_clear()


@pytest.fixture
def make_movie():
    def _make(**overrides) -> Movie:
        data = {
            "id": "m",
            "title": "Demo-Film",
            "original_language": "en",
            "genres": ["Comedy"],
            "world_ids": ["humor"],
            "runtime_min": 100,
            "ml_rating": 3.6,
            "ml_rating_count": 1000,
            "availability": Availability(),
        }
        data.update(overrides)
        return Movie(**data)

    return _make


@pytest.fixture(scope="session")
def db_url():
    from cinesense.core.config import get_settings, load_env_file

    load_env_file()
    url = get_settings().database_url
    if not url:
        pytest.skip("SUPABASE_DB_URL not set")
    return url
