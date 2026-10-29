"""Trailer fallback via the YouTube Data API (search.list: 100 searches/day by default; we stop at 95).
Video ids are cached and re-validated after 30 days (YouTube API policy). Wikidata trailer ids always win."""

import logging
import re
import unicodedata
from datetime import UTC, date, datetime, timedelta
from typing import Protocol

import httpx

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
CACHE_TTL = timedelta(days=30)
log = logging.getLogger(__name__)


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]+", " ", text.lower()).strip()


class TrailerStore(Protocol):
    def get(self, film_id: str) -> tuple[str | None, datetime] | None: ...
    def put(self, film_id: str, video_id: str | None, checked_at: datetime | None = None) -> None: ...
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

    def calls_today(self):
        return self._calls

    def add_call(self):
        self._calls += 1


class PostgresTrailerStore:
    def __init__(self, conn_factory) -> None:
        self._conn = conn_factory

    def get(self, film_id):
        with self._conn() as c:
            row = c.execute(
                "select video_id, checked_at from trailer_cache where film_id = %s", (film_id,)
            ).fetchone()
        return (row[0], row[1]) if row else None

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
        daily_limit: int = 95,
        http: httpx.Client | None = None,
    ):
        self.api_key = api_key
        self.store = store
        self.daily_limit = daily_limit
        self.http = http or httpx.Client()

    def find_trailer(self, film_id: str, title: str, year: int | None) -> str | None:
        cached = self.store.get(film_id)
        if cached is not None:
            video_id, checked_at = cached
            if checked_at.tzinfo is None:
                checked_at = checked_at.replace(tzinfo=UTC)
            if datetime.now(UTC) - checked_at < CACHE_TTL:
                return video_id
        if not self.api_key or self.store.calls_today() >= self.daily_limit:
            return None
        q = f'"{title}" {year or ""} official trailer'.strip()
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
                    "key": self.api_key,
                },
                timeout=8,
            )
            r.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("youtube search failed: %s", exc)
            return None
        want = _norm(title)
        video_id = next(
            (
                i["id"]["videoId"]
                for i in r.json().get("items", [])
                if want in _norm(i["snippet"]["title"]) and "trailer" in i["snippet"]["title"].lower()
            ),
            None,
        )
        self.store.put(film_id, video_id)
        return video_id
