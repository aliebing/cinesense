"""Posters from Wikipedia for films that have none (the Streaming Availability images are budgeted to a few hundred
a month). One request covers 50 articles; only the link is stored in films.poster_url. Resumable: films that
got a poster are skipped on the next run.

    uv run --env-file ../.env python -m cinesense.catalog_import.posters
"""

from __future__ import annotations

import logging
from collections.abc import Callable

log = logging.getLogger(__name__)
BATCH = 50  # the API's maximum titles per request


def fill_posters(
    films: list[tuple[str, str]],
    fetch: Callable[[list[str]], dict[str, str]],
    save: Callable[[str, str], None],
    batch: int = BATCH,
) -> dict:
    """films: (film id, Wikipedia title). A batch that fails is logged and skipped (retried on the next run)."""
    stats = {"films": len(films), "found": 0, "requests": 0}
    for start in range(0, len(films), batch):
        chunk = films[start : start + batch]
        stats["requests"] += 1
        try:
            found = fetch([title for _, title in chunk])
        except Exception as exc:  # noqa: BLE001 — one failed batch must not stop the whole run
            log.warning("poster batch %d failed: %s", start // batch, exc)
            continue
        for film_id, title in chunk:
            if url := found.get(title):
                save(film_id, url)
                stats["found"] += 1
        if stats["requests"] % 20 == 0:
            log.info("posters: %d requests, %d found", stats["requests"], stats["found"])
    return stats


def main() -> None:
    import httpx

    from cinesense.core.config import get_settings
    from cinesense.data_sources.db import connect
    from cinesense.data_sources.wikipedia import fetch_posters

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # one line per request is noise here
    url = get_settings().database_url
    with connect(url) as c:
        films = c.execute(
            "select id, wikipedia_title from films where poster_url is null and wikipedia_title is not null "
            "order by ml_rating_count desc nulls last"
        ).fetchall()

    def save(film_id: str, poster: str) -> None:
        with connect(url) as c:
            c.execute("update films set poster_url = %s where id = %s and poster_url is null", (poster, film_id))
            c.commit()

    with httpx.Client() as client:
        stats = fill_posters([(f, t) for f, t in films], lambda titles: fetch_posters(titles, client), save)
    log.info("done: %s", stats)


if __name__ == "__main__":
    main()
