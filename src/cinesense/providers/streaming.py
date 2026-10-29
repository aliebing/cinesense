"""Streaming availability in Germany via the Streaming Availability API (Movie of the Night).

Free plan: 1,000 requests/month — every call goes through a cache and a monthly budget guard.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

import httpx

from cinesense.domain.models import StreamingOption

BASE_URL = "https://api.movieofthenight.com/v4"
STREAMING_TTL = timedelta(days=7)
IMAGES_TTL = timedelta(days=200)  # signed image URLs stay valid ~280 days
BROWSE_TTL = timedelta(days=1)
log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ImageSet:
    vertical_poster: str | None
    horizontal_poster: str | None  # title art in the image
    horizontal_backdrop: str | None  # no text


class StreamingStore(Protocol):
    def get(self, key: str) -> tuple[dict, datetime] | None: ...
    def put(self, key: str, payload: dict, fetched_at: datetime | None = None) -> None: ...
    def calls_this_month(self) -> int: ...
    def add_call(self) -> None: ...


class MemoryStreamingStore:
    def __init__(self) -> None:
        self._data: dict[str, tuple[dict, datetime]] = {}
        self._calls = 0

    def get(self, key: str) -> tuple[dict, datetime] | None:
        return self._data.get(key)

    def put(self, key: str, payload: dict, fetched_at: datetime | None = None) -> None:
        self._data[key] = (payload, fetched_at or datetime.now(UTC))

    def calls_this_month(self) -> int:
        return self._calls

    def add_call(self) -> None:
        self._calls += 1


class PostgresStreamingStore:
    """streaming_cache holds per-film payloads; keys starting with 'browse:' live in browse_cache."""

    def __init__(self, conn_factory) -> None:
        self._conn = conn_factory

    def _table(self, key: str) -> tuple[str, str]:
        return ("browse_cache", "key") if key.startswith("browse:") else ("streaming_cache", "imdb_id")

    def get(self, key: str) -> tuple[dict, datetime] | None:
        table, col = self._table(key)
        with self._conn() as c:
            row = c.execute(f"select payload, fetched_at from {table} where {col} = %s", (key,)).fetchone()
        return (row[0], row[1]) if row else None

    def put(self, key: str, payload: dict, fetched_at: datetime | None = None) -> None:
        from psycopg.types.json import Jsonb

        table, col = self._table(key)
        with self._conn() as c:
            c.execute(
                f"insert into {table} ({col}, payload, fetched_at) values (%s, %s, %s) "
                f"on conflict ({col}) do update "
                "set payload = excluded.payload, fetched_at = excluded.fetched_at",
                (key, Jsonb(payload), fetched_at or datetime.now(UTC)),
            )
            c.commit()

    def calls_this_month(self) -> int:
        month = datetime.now(UTC).strftime("%Y-%m")
        with self._conn() as c:
            row = c.execute("select calls from api_budget where month = %s", (month,)).fetchone()
        return row[0] if row else 0

    def add_call(self) -> None:
        month = datetime.now(UTC).strftime("%Y-%m")
        with self._conn() as c:
            c.execute(
                "insert into api_budget (month, calls) values (%s, 1) "
                "on conflict (month) do update set calls = api_budget.calls + 1",
                (month,),
            )
            c.commit()


def _fresh(entry: tuple[dict, datetime] | None, ttl: timedelta) -> dict | None:
    if entry is None:
        return None
    payload, fetched_at = entry
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=UTC)
    return payload if datetime.now(UTC) - fetched_at < ttl else None


class StreamingClient:
    def __init__(
        self,
        api_key: str | None,
        store: StreamingStore,
        monthly_limit: int = 900,
        http: httpx.Client | None = None,
    ):
        self.api_key = api_key
        self.store = store
        self.monthly_limit = monthly_limit
        self.http = http or httpx.Client()

    def _request(self, path: str, params: dict) -> httpx.Response | None:
        if not self.api_key or self.store.calls_this_month() >= self.monthly_limit:
            return None
        try:
            self.store.add_call()
            return self.http.get(
                f"{BASE_URL}{path}", params=params, headers={"X-API-Key": self.api_key}, timeout=5
            )
        except httpx.HTTPError as exc:
            log.warning("streaming API error: %s", exc)
            return None

    def _show(self, imdb_id: str, ttl: timedelta = STREAMING_TTL) -> dict | None:
        cached = _fresh(self.store.get(imdb_id), ttl)
        if cached is not None:
            return cached
        r = self._request(f"/shows/{imdb_id}", {"country": "de", "output_language": "en"})
        if r is None:
            return None
        if r.status_code == 404:
            self.store.put(imdb_id, {"notFound": True})
            return {"notFound": True}
        if r.status_code != 200:
            log.warning("streaming API status %s for %s", r.status_code, imdb_id)
            return None
        payload = r.json()
        self.store.put(imdb_id, payload)
        return payload

    def get_de(self, imdb_id: str) -> list[StreamingOption] | None:
        """DE options, [] if known not available, None if unknown (no key, budget, error)."""
        payload = self._show(imdb_id)
        if payload is None:
            return None
        return options_from_payload(payload)

    def images(self, imdb_id: str) -> ImageSet | None:
        payload = _fresh(self.store.get(imdb_id), IMAGES_TTL) or self._show(imdb_id)
        return images_from_payload(payload) if payload else None

    def browse(self, genre: str, cursor: str | None = None) -> tuple[list[dict], str | None]:
        key = f"browse:{genre}:{cursor or ''}"
        cached = _fresh(self.store.get(key), BROWSE_TTL)
        if cached is None:
            params = {"country": "de", "show_type": "movie", "genres": genre, "order_by": "popularity_1week"}
            if cursor:
                params["cursor"] = cursor
            r = self._request("/shows/search/filters", params)
            if r is None or r.status_code != 200:
                return [], None
            cached = r.json()
            self.store.put(key, cached)
            for show in cached.get("shows", []):  # each show doubles as a per-film cache entry
                if show.get("imdbId"):
                    self.store.put(show["imdbId"], show)
        return cached.get("shows", []), cached.get("nextCursor") if cached.get("hasMore") else None


def options_from_payload(payload: dict) -> list[StreamingOption]:
    if payload.get("notFound"):
        return []
    out = []
    for o in (payload.get("streamingOptions") or {}).get("de", []):
        try:
            out.append(StreamingOption(service=o["service"]["name"], type=o["type"], link=o.get("link")))
        except (KeyError, ValueError):
            continue
    return out


def images_from_payload(payload: dict) -> ImageSet:
    s = payload.get("imageSet") or {}

    def pick(kind: str, size: str) -> str | None:
        sizes = s.get(kind) or {}
        return sizes.get(size) or next(iter(sizes.values()), None)

    return ImageSet(
        pick("verticalPoster", "w480"), pick("horizontalPoster", "w720"), pick("horizontalBackdrop", "w1080")
    )
