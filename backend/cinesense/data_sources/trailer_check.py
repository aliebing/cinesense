"""Is a YouTube trailer actually playable as an embed here? Many Wikidata trailer ids are deleted, private,
not embeddable, blocked in Germany or age-restricted.

With a YouTube API key the video status decides (videos.list: 1 quota unit for up to 50 videos, own small daily
budget next to the trailer search): embeddable, public or unlisted, not region-blocked for Germany, not
age-restricted. Without a key, or when the API fails or its budget is used up, YouTube's public oEmbed endpoint
(no key, no quota) answers 200 for embeddable videos; it cannot see region blocks, which the player then reports
(report)."""

import logging
import threading
import time
from collections import defaultdict, deque
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import httpx

from cinesense.core.models import Movie

OEMBED_URL = "https://www.youtube.com/oembed"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
REGION = "DE"
API_BATCH = 50  # ids per videos.list request (YouTube's maximum)
TTL = timedelta(days=30)
MEMORY_TTL_S = 3600  # in-process verdicts expire, so several workers converge on the shared cache
UNKNOWN_TTL_S = 600  # YouTube unreachable or rate-limiting: don't ask again for 10 minutes
REPORTS_PER_HOUR = 20  # per browser id
_PREFIX = "check:"  # rows in trailer_cache keyed "check:<video id>"; video_id column = id if playable, else NULL
_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="oembed")  # small: leaves DB connections free
log = logging.getLogger(__name__)


class TrailerChecker:
    def __init__(
        self, store, http: httpx.Client | None = None, api_key: str | None = None, daily_api_calls: int = 500
    ) -> None:
        self.store = store
        self.http = http or httpx.Client()
        self.api_key = api_key
        self.daily_api_calls = daily_api_calls  # counted per process; a restart only ever resets it to zero
        self._api_day: str | None = None
        self._api_used = 0
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

    def _api_call_allowed(self) -> bool:
        today = datetime.now(UTC).date().isoformat()
        with self._lock:
            if today != self._api_day:
                self._api_day, self._api_used = today, 0
            if not self.api_key or self._api_used >= self.daily_api_calls:
                return False
            self._api_used += 1
            return True

    def _ask_api(self, video_ids: list[str]) -> list[str]:
        """Status verdicts via the Data API; returns the ids it could not answer (no key, budget, failure)."""
        for start in range(0, len(video_ids), API_BATCH):
            chunk = video_ids[start : start + API_BATCH]
            if not self._api_call_allowed():
                return video_ids[start:]
            try:
                r = self.http.get(
                    VIDEOS_URL,
                    params={"part": "status,contentDetails", "id": ",".join(chunk), "maxResults": API_BATCH},
                    headers={"X-goog-api-key": self.api_key},  # header, so the key never appears in URLs or logs
                    timeout=8,
                )
            except httpx.HTTPError as exc:
                log.warning("YouTube status check failed: %s", type(exc).__name__)
                return video_ids[start:]
            if r.status_code != 200:
                log.warning("YouTube status check status %s", r.status_code)
                return video_ids[start:]
            found = {item["id"]: item for item in r.json().get("items", [])}
            for vid in chunk:  # an id YouTube does not return is deleted or private
                self._remember(vid, vid in found and _plays_here(found[vid]))
        return []

    def _check(self, video_ids: list[str], parallel: bool = True) -> None:
        rest = self._ask_api(video_ids)
        if parallel:
            list(_POOL.map(self._ask_youtube, rest))
        else:
            for vid in rest:
                self._ask_youtube(vid)

    def playable_ids(self, video_ids: Iterable[str]) -> list[str]:
        """The ids (in order) not known to fail; unknown ones are checked first (the trailer search uses this)."""
        ids = list(dict.fromkeys(video_ids))
        missing = [k for k in ids if not self._memory(k)[0]]
        if missing:
            self._from_store(missing)
        self._check([k for k in ids if not self._memory(k)[0]])
        return [k for k in ids if self._memory(k) != (True, False)]

    def playable(self, video_id: str) -> bool | None:
        """True/False when known; None when YouTube could not be asked (then the trailer is kept)."""
        found, verdict = self._memory(video_id)
        if found:
            return verdict
        self._from_store([video_id])
        found, verdict = self._memory(video_id)
        if found:
            return verdict
        self._check([video_id])
        return self._memory(video_id)[1]

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
        self._check(self._unknown(movies))
        return self._apply(movies)

    def filter_known(self, movies: list[Movie]) -> list[Movie]:
        """Like filter_playable, but never waits: unknown ids are checked in the background and count as
        playable for now (the player reports any that fail)."""
        unknown = self._unknown(movies)
        with self._lock:
            fresh = [k for k in unknown if k not in self._pending]
            self._pending.update(fresh)
        if fresh:
            _POOL.submit(self._warm, fresh)
        return self._apply(movies)

    def _warm(self, keys: list[str]) -> None:
        try:
            self._check(keys, parallel=False)  # already on a pool thread: no nested pool waits
        finally:
            with self._lock:
                self._pending.difference_update(keys)

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


def _plays_here(item: dict) -> bool:
    """A videos.list item plays as an embed in Germany for everyone."""
    status = item.get("status") or {}
    details = item.get("contentDetails") or {}
    region = details.get("regionRestriction") or {}
    return (
        bool(status.get("embeddable"))
        and status.get("privacyStatus") in ("public", "unlisted")
        and REGION not in region.get("blocked", [])
        and ("allowed" not in region or REGION in region["allowed"])
        and (details.get("contentRating") or {}).get("ytRating") != "ytAgeRestricted"
    )
