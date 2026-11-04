from pathlib import Path

from cinesense.core.config import get_settings


def test_settings_read_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://x")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or")
    monkeypatch.setenv("STREAMING_AVAILABILITY_API_KEY", "sa")
    monkeypatch.setenv("MOVIELENS_DB_PATH", "/tmp/ml.db")
    monkeypatch.setenv("YOUTUBE_API_KEY", "yt")
    s = get_settings()
    assert s.database_url == "postgresql://x"
    assert s.openrouter_api_key == "or"
    assert s.streaming_api_key == "sa"
    assert s.movielens_db_path == Path("/tmp/ml.db")
    assert s.youtube_api_key == "yt"


def test_settings_missing_is_none(monkeypatch):
    for k in [
        "SUPABASE_DB_URL",
        "OPENROUTER_API_KEY",
        "STREAMING_AVAILABILITY_API_KEY",
        "MOVIELENS_DB_PATH",
        "YOUTUBE_API_KEY",
    ]:
        monkeypatch.delenv(k, raising=False)
    s = get_settings()
    assert s.database_url is None and s.streaming_api_key is None and s.movielens_db_path is None
    assert s.streaming_monthly_limit == 900
    assert s.youtube_daily_limit == 90
    assert s.youtube_check_daily_calls == 500
