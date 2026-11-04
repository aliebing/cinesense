"""Is a YouTube trailer actually playable as an embed? Many Wikidata trailer ids are deleted, private or
not embeddable. YouTube's public oEmbed endpoint (no key, no quota) answers 200 for playable embeds and
401/403/404 otherwise. Region blocks are invisible to oEmbed, so the player reports those (report)."""

import logging
import threading
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import httpx

from cinesense.core.models import Movie

OEMBED_URL = "https://www.youtube.com/oembed"
TTL = timedelta(days=30)
MEMORY_TTL_S = 3600  # in-process verdicts expire, so several workers converge on the shared cache
UNKNOWN_TTL_S = 600  # YouTube unreachable or rate-limiting: don't ask again for 10 minutes
REPORTS_PER_HOUR = 20  # per browser id
_PREFIX = "check:"  # rows in trailer_cache keyed "check:<video id>"; video_id column = id if playable, else NULL
_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="oembed")  # small: leaves DB connections free
log = logging.getLogger(__name__)


class TrailerChecker:
    def __init__(self, store, http: httpx.Client | None = None) -> None:
        self.store = store
        self.http = http or httpx.Client()
        self._known: dict[str, tuple[bool | None, float]] = {}
        self._served: set[str] = set()
        self._reports: defaultdict[str, deque] = defaultdict(deque)
        self._pending: set[str] = set()
        self._lock = threading.Lock()

    # --- memory ---------------------------------------------------------------
    def _memory(self, video_id: str) -> tuple[bool, bool | None]:
        """(found, verdict) from the in-process cache, honouring the TTLs."""
        with self._lock:
            hit = self._known.get(video_id)
        if hit is None:
            return False, None
        verdict, at = hit
        ttl = UNKNOWN_TTL_S if verdict is None else MEMORY_TTL_S
        return (time.monotonic() - at < ttl), verdict

    def _remember(self, video_id: str, verdict: bool | None, persist: bool = True) -> None:
        with self._lock:
            self._known[video_id] = (verdict, time.monotonic())
        if persist and verdict is not None:
            self.store.put(_PREFIX + video_id, video_id if verdict else None)

    def _from_store(self, keys: list[str]) -> None:
        """One batch read of stored verdicts into memory."""
        rows = (
            self.store.get_many([_PREFIX + k for k in keys])
            if hasattr(self.store, "get_many")
            else {_PREFIX + k: self.store.get(_PREFIX + k) for k in keys}
        )
        now = datetime.now(UTC)
        for k in keys:
            row = rows.get(_PREFIX + k)
            if row is not None and now - row[1] < TTL:
                self._remember(k, row[0] is not None, persist=False)

    # --- checks -----------------------------------------------------------------
    def _ask_youtube(self, video_id: str) -> bool | None:
        try:
            r = self.http.get(
                OEMBED_URL, params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"}, timeout=8
            )
        except httpx.HTTPError as exc:
            log.warning("oEmbed check failed: %s", type(exc).__name__)
            self._remember(video_id, None)
            return None
        if r.status_code >= 500 or r.status_code == 429:
            self._remember(video_id, None)
            return None
        ok = r.status_code == 200
        self._remember(video_id, ok)
        return ok

    def playable(self, video_id: str) -> bool | None:
        """True/False when known; None when YouTube could not be asked (then the trailer is kept)."""
        found, verdict = self._memory(video_id)
        if found:
            return verdict
        self._from_store([video_id])
        found, verdict = self._memory(video_id)
        return verdict if found else self._ask_youtube(video_id)

    def _unknown(self, movies: list[Movie]) -> list[str]:
        keys = sorted({m.youtube_key for m in movies if m.youtube_key})
        with self._lock:
            self._served.update(keys)
        missing = [k for k in keys if not self._memory(k)[0]]
        if missing:
            self._from_store(missing)
        return [k for k in keys if not self._memory(k)[0]]

    def _apply(self, movies: list[Movie]) -> list[Movie]:
        for m in movies:
            if m.youtube_key and self._memory(m.youtube_key) == (True, False):
                m.youtube_key = None
        return movies

    def filter_playable(self, movies: list[Movie]) -> list[Movie]:
        """Drops trailer ids that are known not to play (in place); asks YouTube for unknown ones and waits."""
        unknown = self._unknown(movies)
        list(_POOL.map(self._ask_youtube, unknown))
        return self._apply(movies)

    def filter_known(self, movies: list[Movie]) -> list[Movie]:
        """Like filter_playable, but never waits: unknown ids are checked in the background and count as
        playable for now (the player reports any that fail)."""
        for key in self._unknown(movies):
            with self._lock:
                if key in self._pending:
                    continue
                self._pending.add(key)
            _POOL.submit(self._warm, key)
        return self._apply(movies)

    def _warm(self, key: str) -> None:
        try:
            self._ask_youtube(key)
        finally:
            with self._lock:
                self._pending.discard(key)

    # --- reports from the player ---------------------------------------------
    def served(self, video_id: str) -> bool:
        with self._lock:
            return video_id in self._served

    def report(self, video_id: str, user: str, known: bool) -> bool:
        """The embedded player could not play this trailer. Only ids CineSense actually offers count, and each
        browser id may report a limited number per hour, so nobody can switch off all trailers."""
        if not known:
            return False
        now = time.monotonic()
        with self._lock:
            recent = self._reports[user]
            while recent and now - recent[0] > 3600:
                recent.popleft()
            if len(recent) >= REPORTS_PER_HOUR:
                return False
            recent.append(now)
        self.mark_bad(video_id)
        return True

    def mark_bad(self, video_id: str) -> None:
        self._remember(video_id, False)
