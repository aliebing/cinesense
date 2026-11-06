"""The homepage rows: the most popular films per mood world, each film in one row only.

The answer is the same for every visitor, so it is built once and kept for HOME_TTL seconds; a stale copy is
served while a background thread builds the next one. It carries only what a tile needs (the full film costs
~3 KB, mostly signed image URLs and the plot)."""

import logging
import threading
import time
from collections.abc import Callable

from cinesense.core.models import Movie
from cinesense.core.worlds import WORLDS
from cinesense.web_api.images import with_images

log = logging.getLogger(__name__)

ROW_SIZE = 16
HOME_TTL = 300  # seconds
TILE_FIELDS = {"id", "title", "year", "world_ids", "youtube_key", "horizontal_poster_url", "backdrop_url"}


def row_trailers(movies: list[Movie], checker, trailers) -> list[Movie]:
    """Trailers for tiles that play on hover, without waiting or spending quota: known-bad ids drop out (unknown
    ones are checked in the background), and a film left without one gets the trailer a YouTube search already
    found for it (the Matrix: its Wikidata trailer is gone, the detail page found another)."""
    if checker is not None:
        checker.filter_known(movies)
    cached = getattr(trailers, "cached", None)
    missing = [m for m in movies if m.youtube_key is None]
    if cached is None or not missing:
        return movies
    found = cached([m.id for m in missing])
    for m in missing:
        m.youtube_key = found.get(m.id)
    if checker is not None:
        checker.filter_known(missing)  # a reported fallback trailer is never offered again
    return movies


def build_home(provider, streaming, checker, trailers) -> dict:
    movies = provider.list_movies()
    pools: dict[str, list[Movie]] = {}
    for w in WORLDS:
        in_world = sorted((m for m in movies if w.id in m.world_ids), key=lambda m: m.ml_rating_count, reverse=True)
        pool = [m.model_copy(deep=True) for m in in_world[: ROW_SIZE * 4]]
        row_trailers(pool, checker, trailers)
        # popular films with a playable trailer first, so hovering a tile usually plays something
        pools[w.id] = sorted(pool, key=lambda m: (m.youtube_key is not None, m.ml_rating_count), reverse=True)
    rows: dict[str, list[Movie]] = {w.id: [] for w in WORLDS}
    used: set[str] = set()  # each film in one row only; worlds take turns so none is starved
    for _ in range(ROW_SIZE):
        for w in WORLDS:
            nxt = next((m for m in pools[w.id] if m.id not in used), None)
            if nxt is not None:
                rows[w.id].append(nxt)
                used.add(nxt.id)
    for w in WORLDS:
        rows[w.id] = [with_images(m, provider, streaming) for m in rows[w.id]]
    titles: list[str] = []
    for w in WORLDS:
        titles += [m.title for m in rows[w.id][:2] if m.title not in titles]
    return {
        "worlds": [w.model_dump() for w in WORLDS],
        "rows": {wid: _tiles(films) for wid, films in rows.items()},
        "titles": titles,
    }


def _tiles(films: list[Movie]) -> list[dict]:
    """A tile shows the wide poster, else the backdrop; the row's first backdrop is also its world's hero picture.
    Every other backdrop is left out: the signed image URLs are ~450 characters each and made up most of the
    answer."""
    out, hero = [], False
    for m in films:
        tile = m.model_dump(include=TILE_FIELDS)
        if m.backdrop_url and not hero:
            hero = True
        elif m.horizontal_poster_url:
            tile["backdrop_url"] = None
        out.append(tile)
    return out


class HomeCache:
    """Keeps the built homepage for `ttl` seconds; only the very first request waits for the build."""

    def __init__(self, ttl: float = HOME_TTL) -> None:
        self.ttl = ttl
        self._value: dict | None = None
        self._built_at = 0.0
        self._building = False
        self._lock = threading.Lock()

    def get(self, build: Callable[[], dict]) -> dict:
        with self._lock:
            value = self._value
            stale = value is not None and time.monotonic() - self._built_at > self.ttl
            rebuild = stale and not self._building
            if rebuild:
                self._building = True
        if value is None:
            return self._store(build())
        if rebuild:
            threading.Thread(target=self._rebuild, args=(build,), daemon=True).start()
        return value

    def _store(self, value: dict) -> dict:
        with self._lock:
            self._value, self._built_at = value, time.monotonic()
        return value

    def _rebuild(self, build: Callable[[], dict]) -> None:
        try:
            self._store(build())
        except Exception:  # noqa: BLE001 — keep serving the old rows; the next request tries again
            log.exception("homepage rebuild failed")
        finally:
            with self._lock:
                self._building = False
