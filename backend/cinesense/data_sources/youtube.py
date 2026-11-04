"""Trailer fallback via the YouTube Data API (search.list costs 100 of the 10,000 daily units: we stop at 90
searches, leaving room for the status checks in trailer_check.py).
Video ids are cached and re-validated after 30 days (YouTube API policy). Wikidata trailer ids always win."""

import logging
import re
import unicodedata
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Protocol

import httpx

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
CACHE_TTL = timedelta(days=30)
log = logging.getLogger(__name__)


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]+", " ", text.lower()).strip()


def _plain_title(title: str) -> str:
    """MovieLens style "Road Home, The (Wo de fu qin mu qin)" -> "The Road Home"."""
    title = re.sub(r"\s*\([^)]*\)\s*$", "", title).strip()
    m = re.match(r"^(.*), (The|A|An|Les|Le|La|L'|Die|Der|Das)$", title)
    return f"{m.group(2)} {m.group(1)}" if m else title


def _title_matches(title: str, video_title: str) -> bool:
    """Most of the title's words (3+ letters or digits) appear in the video title: subtitles like "Episode IV"
    may be missing, but a different film ("Star Trek" for "Star Wars") is not accepted."""
    words = [w for w in _norm(title).split() if len(w) > 2 or w.isdigit()] or _norm(title).split()
    have = set(_norm(video_title).split())
    return bool(words) and sum(w in have for w in words) >= 0.75 * len(words)


def _fresh(checked_at: datetime) -> bool:
    if checked_at.tzinfo is None:
        checked_at = checked_at.replace(tzinfo=UTC)
    return datetime.now(UTC) - checked_at < CACHE_TTL


class TrailerStore(Protocol):
    def get(self, film_id: str) -> tuple[str | None, datetime] | None: ...
    def put(self, film_id: str, video_id: str | None, checked_at: datetime | None = None) -> None: ...
    def get_many(self, film_ids: list[str]) -> dict[str, tuple[str | None, datetime]]: ...
    def calls_today(self) -> int: ...
    def add_call(self) -> None: ...


class MemoryTrailerStore:
    def __init__(self) -> None:
        self._data: dict[str, tuple[str | None, datetime]] = {}
        self._calls = 0

    def get(self, film_id):
        return self._data.get(film_id)

    def put(self, film_id, video_id, checked_at=None):
        self._data[film_id] = (video_id, checked_at or datetime.now(UTC))

    def get_many(self, film_ids):
        return {f: self._data[f] for f in film_ids if f in self._data}

    def calls_today(self):
        return self._calls

    def add_call(self):
        self._calls += 1


class PostgresTrailerStore:
    def __init__(self, conn_factory) -> None:
        self._conn = conn_factory

    def get(self, film_id):
        with self._conn() as c:
            row = c.execute("select video_id, checked_at from trailer_cache where film_id = %s", (film_id,)).fetchone()
        return (row[0], row[1]) if row else None

    def get_many(self, film_ids):
        if not film_ids:
            return {}
        with self._conn() as c:
            rows = c.execute(
                "select film_id, video_id, checked_at from trailer_cache where film_id = any(%s)", (list(film_ids),)
            ).fetchall()
        return {r[0]: (r[1], r[2]) for r in rows}

    def put(self, film_id, video_id, checked_at=None):
        with self._conn() as c:
            c.execute(
                "insert into trailer_cache (film_id, video_id, checked_at) values (%s, %s, %s) "
                "on conflict (film_id) do update "
                "set video_id = excluded.video_id, checked_at = excluded.checked_at",
                (film_id, video_id, checked_at or datetime.now(UTC)),
            )
            c.commit()

    def calls_today(self):
        with self._conn() as c:
            row = c.execute("select calls from youtube_quota where day = %s", (date.today(),)).fetchone()
        return row[0] if row else 0

    def add_call(self):
        with self._conn() as c:
            c.execute(
                "insert into youtube_quota (day, calls) values (%s, 1) "
                "on conflict (day) do update set calls = youtube_quota.calls + 1",
                (date.today(),),
            )
            c.commit()


class YouTubeTrailerClient:
    def __init__(
        self,
        api_key: str | None,
        store: TrailerStore,
        daily_limit: int = 90,
        http: httpx.Client | None = None,
        playable: Callable[[list[str]], list[str]] | None = None,
    ):
        self.api_key = api_key
        self.store = store
        self.daily_limit = daily_limit
        self.http = http or httpx.Client()
        self.playable = playable  # keeps the ids that play here (TrailerChecker.playable_ids); None: keep all

    def cached(self, film_ids: list[str]) -> dict[str, str]:
        """Trailers an earlier search already found (film id -> video id), from the cache only: no quota, no
        request. The tile rows use them where the Wikidata trailer is missing or does not play."""
        fresh = {}
        for film_id, (video_id, checked_at) in self.store.get_many(film_ids).items():
            if video_id and _fresh(checked_at):
                fresh[film_id] = video_id
        return fresh

    def find_trailer(self, film_id: str, title: str, year: int | None) -> str | None:
        cached = self.store.get(film_id)
        if cached is not None and _fresh(cached[1]):
            return cached[0]
        if not self.api_key or self.store.calls_today() >= self.daily_limit:
            return None
        plain = _plain_title(title)
        q = f'"{plain}" {year or ""} official trailer'.strip()
        try:
            self.store.add_call()
            r = self.http.get(
                SEARCH_URL,
                params={
                    "part": "snippet",
                    "type": "video",
                    "maxResults": 5,
                    "videoEmbeddable": "true",
                    "q": q,
                },
                headers={"X-goog-api-key": self.api_key},  # header, so the key never appears in URLs or logs
                timeout=8,
            )
        except httpx.HTTPError as exc:
            log.warning("youtube search failed: %s", type(exc).__name__)
            return None
        if r.status_code != 200:
            log.warning("youtube search status %s", r.status_code)
            return None
        matches = [
            i["id"]["videoId"]
            for i in r.json().get("items", [])
            if _title_matches(plain, i["snippet"]["title"]) and "trailer" in i["snippet"]["title"].lower()
        ]
        if matches and self.playable is not None:
            matches = self.playable(matches)  # a hit blocked here (region, age, embedding) gives way to the next
        video_id = matches[0] if matches else None
        self.store.put(film_id, video_id)
        return video_id
