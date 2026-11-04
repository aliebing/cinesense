"""Settings from the environment (.env at the repo root): database, OpenRouter, streaming and YouTube keys."""

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]  # backend/cinesense/core/config.py -> repo root


def load_env_file(path: Path = REPO_ROOT / ".env") -> None:
    """Minimal .env loader (KEY=VALUE lines); existing environment variables win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _env(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None


@dataclass(frozen=True)
class Settings:
    database_url: str | None
    openrouter_api_key: str | None
    streaming_api_key: str | None
    youtube_api_key: str | None
    movielens_db_path: Path | None
    llm_model: str = "anthropic/claude-haiku-5.5"
    streaming_monthly_limit: int = 900
    youtube_daily_limit: int = 95
    chat_per_minute: int = 6  # agent turns per visitor (chat and /api/inspect)
    chat_per_day: int = 40
    chat_site_per_day: int = 800  # all visitors together (~$1 a day at the measured $0.0013 per turn)


def get_settings() -> Settings:
    ml = _env("MOVIELENS_DB_PATH")
    return Settings(
        database_url=_env("SUPABASE_DB_URL"),
        openrouter_api_key=_env("OPENROUTER_API_KEY"),
        streaming_api_key=_env("STREAMING_AVAILABILITY_API_KEY"),
        youtube_api_key=_env("YOUTUBE_API_KEY"),
        movielens_db_path=Path(ml) if ml else None,
        llm_model=_env("CINESENSE_LLM_MODEL") or "anthropic/claude-haiku-5.5",
        chat_per_minute=int(_env("CHAT_LIMIT_PER_MINUTE") or 6),
        chat_per_day=int(_env("CHAT_LIMIT_PER_DAY") or 40),
        chat_site_per_day=int(_env("CHAT_LIMIT_SITE_PER_DAY") or 800),
    )
