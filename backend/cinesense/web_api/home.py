"""The homepage rows per mood world: its newest top-rated films and its top classics, each film shown once.

The answer is the same for every visitor, so it is built once and kept for HOME_TTL seconds; a stale copy is
served while a background thread builds the next one. It carries only what a tile needs (the full film costs
~3 KB, mostly signed image URLs and the plot)."""

import logging
import threading
import time
from collections.abc import Callable

from cinesense.core.models import Movie
from cinesense.core.worlds import WORLDS
from cinesense.search.rating import catalogue_rating
from cinesense.web_api.images import with_images

log = logging.getLogger(__name__)

ROW_SIZE = 10  # films per row; a world shows two rows (newest top-rated, top classics)
NEWEST_YEARS = 10  # "newest": from the last ten years of the catalogue
CLASSIC_BEFORE = 2000  # "classics": made before this year
POOL = 40  # the best-known films each row is chosen from (Bayesian rating over them)
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
    newest_year = max((m.year for m in movies if m.year), default=CLASSIC_BEFORE + NEWEST_YEARS)
    recent_from = newest_year - NEWEST_YEARS + 1

    def pool(world_id: str, keep) -> list[Movie]:
        """The best-known films of a world that `keep` accepts, best-rated first (Bayesian, so a handful of votes
        cannot win)."""
        in_world = sorted(
            (m for m in movies if world_id in m.world_ids and m.year and keep(m.year)),
            key=lambda m: m.ml_rating_count,
            reverse=True,
        )
        films = [m.model_copy(deep=True) for m in in_world[:POOL]]
        row_trailers(films, checker, trailers)
        return sorted(films, key=lambda m: catalogue_rating(m.ml_rating, m.ml_rating_count), reverse=True)

    pools = {
        kind: {w.id: pool(w.id, keep) for w in WORLDS}
        for kind, keep in (("newest", lambda y: y >= recent_from), ("classics", lambda y: y < CLASSIC_BEFORE))
    }
    chosen: dict[str, dict[str, list[Movie]]] = {kind: {w.id: [] for w in WORLDS} for kind in pools}
    used: set[str] = set()  # each film once; the worlds take turns so none is starved
    for _ in range(ROW_SIZE):
        for kind in pools:
            for w in WORLDS:
                nxt = next((m for m in pools[kind][w.id] if m.id not in used), None)
                if nxt is not None:
                    chosen[kind][w.id].append(nxt)
                    used.add(nxt.id)
    for kind in chosen:
        for w in WORLDS:
            chosen[kind][w.id] = [with_images(m, provider, streaming) for m in chosen[kind][w.id]]
    # the films of a world in the order the page uses them: its hero picture and drifting titles come from the
    # newest top-rated first, then the classics
    rows = {w.id: chosen["newest"][w.id] + chosen["classics"][w.id] for w in WORLDS}
    titles: list[str] = []
    for w in WORLDS:
        titles += [m.title for m in rows[w.id][:2] if m.title not in titles]
    return {
        "worlds": [w.model_dump() for w in WORLDS],
        "rows": {wid: _tiles(films) for wid, films in rows.items()},
        "newest": {w.id: [t["id"] for t in _tiles(chosen["newest"][w.id])] for w in WORLDS},
        "newest_from": recent_from,
        "classics_before": CLASSIC_BEFORE,
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
