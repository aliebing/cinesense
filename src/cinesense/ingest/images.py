"""One-off bulk image fill from the Streaming Availability catalogue search.

One request returns a whole page of films with their images, so this fills far more films per request than the
per-film lookups the app makes on demand. It only finds films that currently stream in Germany; the rest keep
filling on demand. Every request counts against the shared monthly budget; `--max-calls` leaves the remainder for
the app's streaming checks.

    uv run --env-file .env python -m cinesense.ingest.images --max-calls 400
    uv run --env-file .env python -m cinesense.ingest.images --genres action,thriller,scifi   # continue elsewhere

Pages already fetched this week come from the cache and cost nothing.
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Callable, Iterable

from cinesense.providers.streaming import images_from_payload

GENRES = [  # Streaming Availability genre ids, most film-rich first
    "drama", "comedy", "action", "thriller", "crime", "adventure", "scifi", "romance", "mystery", "fantasy",
    "animation", "family", "horror", "documentary", "war", "history", "western", "music",
]  # fmt: skip
log = logging.getLogger(__name__)

Browse = Callable[[str, str | None], tuple[list[dict], str | None]]
Save = Callable[[str, str | None, str | None, str | None], int]  # imdb id, poster, horizontal, backdrop -> films set


def prefetch(browse: Browse, save: Save, calls_left: Callable[[], int], genres: Iterable[str] = GENRES) -> dict:
    """Walk the catalogue genre by genre, page by page, and store the images of every film the catalogue knows.
    Stops as soon as `calls_left()` reaches zero; a page that fails (budget, outage) ends that genre."""
    stats = {"pages": 0, "shows": 0, "films": 0}
    seen: set[str] = set()
    for genre in genres:
        cursor: str | None = None
        while calls_left() > 0:
            shows, cursor = browse(genre, cursor)
            if not shows:
                break
            stats["pages"] += 1
            for show in shows:
                imdb = show.get("imdbId")
                if not imdb or imdb in seen:
                    continue
                seen.add(imdb)
                stats["shows"] += 1
                img = images_from_payload(show)
                if img.vertical_poster or img.horizontal_poster or img.horizontal_backdrop:
                    stats["films"] += save(imdb, img.vertical_poster, img.horizontal_poster, img.horizontal_backdrop)
            log.info("%s page %d: %d films with new images so far", genre, stats["pages"], stats["films"])
            if cursor is None:
                break
        if calls_left() <= 0:
            break
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--max-calls", type=int, default=400, help="requests this run may use (default 400)")
    parser.add_argument("--order-by", default="popularity_alltime")
    parser.add_argument("--year-max", type=int, default=2020)
    parser.add_argument("--genres", default=",".join(GENRES), help="comma-separated genre ids, in this order")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    from cinesense.config import get_settings
    from cinesense.db import connect
    from cinesense.providers.streaming import PostgresStreamingStore, StreamingClient

    s = get_settings()
    if not (s.streaming_api_key and s.database_url):
        raise SystemExit("STREAMING_AVAILABILITY_API_KEY and SUPABASE_DB_URL are needed")
    store = PostgresStreamingStore(lambda: connect(s.database_url))
    start = store.calls_this_month()
    cap = min(start + args.max_calls, s.streaming_monthly_limit)
    client = StreamingClient(s.streaming_api_key, store, monthly_limit=s.streaming_monthly_limit, image_limit=cap)

    def save(imdb: str, poster: str | None, horizontal: str | None, backdrop: str | None) -> int:
        with connect(s.database_url) as c:
            n = c.execute(
                "update films set poster_url = coalesce(poster_url, %s), "
                "horizontal_poster_url = coalesce(horizontal_poster_url, %s), "
                "backdrop_url = coalesce(backdrop_url, %s), images_fetched_at = now() "
                "where imdb_id = %s and (poster_url is null or horizontal_poster_url is null or backdrop_url is null)",
                (poster, horizontal, backdrop, imdb),
            ).rowcount
            c.commit()
        return n

    def browse(genre: str, cursor: str | None):
        # all-time popularity up to the catalogue's newest MovieLens year: most hits are CineSense films
        return client.browse(genre, cursor, order_by=args.order_by, year_max=args.year_max)

    stats = prefetch(browse, save, lambda: cap - store.calls_this_month(), args.genres.split(","))
    used = store.calls_this_month() - start
    log.info("done: %d requests, %d pages, %d catalogue films, %d CineSense films got images", used, stats["pages"],
             stats["shows"], stats["films"])  # fmt: skip
    log.info("restart the API (docker compose restart api) so it reloads the films")


if __name__ == "__main__":
    main()
