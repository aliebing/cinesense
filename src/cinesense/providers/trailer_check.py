"""Is a YouTube trailer actually playable as an embed? Many Wikidata trailer ids are deleted, private or
not embeddable. YouTube's public oEmbed endpoint (no key, no quota) answers 200 for playable embeds and
401/403/404 otherwise. Region blocks are invisible to oEmbed, so the player reports those (mark_bad)."""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import httpx

from cinesense.domain.models import Movie

OEMBED_URL = "https://www.youtube.com/oembed"
TTL = timedelta(days=30)
_PREFIX = "check:"  # rows in trailer_cache keyed "check:<video id>"; video_id column = id if playable, else NULL
log = logging.getLogger(__name__)


class TrailerChecker:
    def __init__(self, store, http: httpx.Client | None = None) -> None:
        self.store = store
        self.http = http or httpx.Client()
        self._known: dict[str, bool] = {}
        self._lock = threading.Lock()

    def _remember(self, video_id: str, ok: bool, persist: bool = True) -> None:
        with self._lock:
            self._known[video_id] = ok
        if persist:
            self.store.put(_PREFIX + video_id, video_id if ok else None)

    def playable(self, video_id: str) -> bool | None:
        """True/False when known; None when YouTube could not be asked (then the trailer is kept)."""
        with self._lock:
            if video_id in self._known:
                return self._known[video_id]
        cached = self.store.get(_PREFIX + video_id)
        if cached is not None and datetime.now(UTC) - cached[1] < TTL:
            self._remember(video_id, cached[0] is not None, persist=False)
            return cached[0] is not None
        try:
            r = self.http.get(
                OEMBED_URL, params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"}, timeout=8
            )
        except httpx.HTTPError as exc:
            log.warning("oEmbed check failed: %s", type(exc).__name__)
            return None
        if r.status_code >= 500 or r.status_code == 429:
            return None
        ok = r.status_code == 200
        self._remember(video_id, ok)
        return ok

    def mark_bad(self, video_id: str) -> None:
        """The embedded player reported an error (e.g. blocked in Germany): never offer it again."""
        self._remember(video_id, False)

    def filter_playable(self, movies: list[Movie]) -> list[Movie]:
        """Drops trailer ids that are known not to play (in place); checks unknown ids in parallel."""
        keys = sorted({m.youtube_key for m in movies if m.youtube_key})
        if not keys:
            return movies
        with ThreadPoolExecutor(max_workers=8) as pool:
            verdict = dict(zip(keys, pool.map(self.playable, keys), strict=True))
        for m in movies:
            if m.youtube_key and verdict.get(m.youtube_key) is False:
                m.youtube_key = None
        return movies
