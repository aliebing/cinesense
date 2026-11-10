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
    tech_user: str | None = None  # login for /tech and /api/inspect; unset: open (local development)
    tech_password_hash: str | None = None  # bcrypt hash of the password (`make admin-password`)
    llm_model: str = "anthropic/claude-haiku-5.5"
    streaming_monthly_limit: int = 900
    youtube_daily_limit: int = 90  # searches (100 units each) of YouTube's 10,000 units a day
    youtube_check_daily_calls: int = 500  # status checks (1 unit for up to 50 videos each)
    chat_per_minute: int = 6  # agent turns per visitor and minute (chat; the technical view counts on its own)
    chat_per_day: int = 25
    tech_per_day: int = 50  # agent turns per visitor and day on the login-protected technical view (/api/inspect)
    chat_site_per_day: int = 800  # all visitors together (~$1 a day at the measured $0.0013 per turn)
    eval_dir: Path = REPO_ROOT / "evaluation" / "results"  # saved `make eval` runs, shown on /admin/evaluation
    eval_runs_dir: Path = REPO_ROOT / "evaluation" / "results"  # where runs started from /admin/evaluation are saved
    chat_log_days: int = 30  # the visitor log (/admin/visitors) keeps chat turns this long (privacy notice)


def get_settings() -> Settings:
    ml = _env("MOVIELENS_DB_PATH")
    return Settings(
        database_url=_env("SUPABASE_DB_URL"),
        openrouter_api_key=_env("OPENROUTER_API_KEY"),
        streaming_api_key=_env("STREAMING_AVAILABILITY_API_KEY"),
        youtube_api_key=_env("YOUTUBE_API_KEY"),
        movielens_db_path=Path(ml) if ml else None,
        tech_user=_env("TECH_USER"),
        tech_password_hash=_env("TECH_PASSWORD_HASH"),
        llm_model=_env("CINESENSE_LLM_MODEL") or "anthropic/claude-haiku-5.5",
        chat_per_minute=int(_env("CHAT_LIMIT_PER_MINUTE") or 6),
        chat_per_day=int(_env("CHAT_LIMIT_PER_DAY") or 25),
        tech_per_day=int(_env("TECH_LIMIT_PER_DAY") or 50),
        chat_site_per_day=int(_env("CHAT_LIMIT_SITE_PER_DAY") or 800),
        eval_dir=Path(_env("CINESENSE_EVAL_DIR") or REPO_ROOT / "evaluation" / "results"),
        eval_runs_dir=Path(
            _env("CINESENSE_EVAL_RUNS_DIR") or _env("CINESENSE_EVAL_DIR") or REPO_ROOT / "evaluation" / "results"
        ),
    )
