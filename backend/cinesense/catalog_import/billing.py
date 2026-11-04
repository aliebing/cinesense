"""Backfill the billing order of every film's cast from its Wikipedia lead (20 articles per request).

    uv run --env-file .env python -m cinesense.catalog_import.billing   # resumable; skips films already checked

A person search then ranks films an actor leads above those with a small part (see domain/billing.py).
"""

import argparse
import asyncio
import logging
import time

import httpx

from cinesense.core.billing import billing_order, top_cast
from cinesense.data_sources.wikidata import USER_AGENT
from cinesense.data_sources.wikipedia import API_URL

BATCH = 20  # the extracts API returns at most 20 intros per request
log = logging.getLogger(__name__)


async def fetch_leads(titles: list[str], client: httpx.AsyncClient, retries: int = 4) -> dict[str, str]:
    """Plain-text intro section per asked title (redirects followed); missing articles are left out."""
    params = {
        "action": "query",
        "prop": "extracts",
        "exintro": "1",
        "explaintext": "1",
        "exlimit": str(BATCH),
        "redirects": "1",
        "titles": "|".join(titles),
        "format": "json",
        "formatversion": "1",
    }
    for attempt in range(retries):
        r = await client.get(API_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=30)
        if r.status_code in (429, 500, 502, 503, 504):
            await asyncio.sleep(2**attempt * 2)
            continue
        r.raise_for_status()
        q = r.json().get("query", {})
        by_title = {p["title"]: p.get("extract") for p in q.get("pages", {}).values() if "missing" not in p}
        hops = {h["from"]: h["to"] for h in q.get("normalized", []) + q.get("redirects", [])}
        out = {}
        for asked in titles:
            final = asked
            for _ in range(3):  # normalised, then redirected
                final = hops.get(final, final)
            if by_title.get(final):
                out[asked] = by_title[final]
        return out
    r.raise_for_status()  # still failing: an error (retried next run), not "no lead"
    return {}


async def backfill(conn, max_films: int | None = None, concurrency: int = 3, ids: list[str] | None = None) -> int:
    where = "wikipedia_title is not null and billing_checked_at is null"
    params: tuple = ()
    if ids is not None:
        where += " and id = any(%s)"
        params = (ids,)
    todo = conn.execute(
        f"select id, wikipedia_title from films where {where} order by ml_rating_count desc nulls last, id", params
    ).fetchall()
    if max_films:
        todo = todo[:max_films]
    log.info("Films to check: %d", len(todo))
    sem = asyncio.Semaphore(concurrency)
    started, done = time.monotonic(), 0
    async with httpx.AsyncClient() as client:

        async def one(group):
            async with sem:
                try:
                    return group, await fetch_leads([t for _, t in group], client)
                except httpx.HTTPError as exc:
                    log.warning("lead fetch failed: %s", exc)
                    return group, None

        groups = [todo[i : i + BATCH] for i in range(0, len(todo), BATCH)]
        for i in range(0, len(groups), 10):
            for group, leads in await asyncio.gather(*(one(g) for g in groups[i : i + 10])):
                if leads is None:
                    continue  # retried next run
                ids_ = [f for f, _ in group]
                cast = conn.execute(
                    "select film_id, name from film_people where role = 'cast' and film_id = any(%s) order by ord",
                    (ids_,),
                ).fetchall()
                rows, tops = [], []
                for film_id, title in group:
                    names = [n for f, n in cast if f == film_id]
                    order = billing_order(leads.get(title, ""), names)
                    rows += [(order.get(n), film_id, n) for n in names]
                    tops.append((top_cast(names, order), film_id))
                with conn.cursor() as cur:
                    cur.executemany(
                        "update film_people set billing = %s where film_id = %s and name = %s and role = 'cast'", rows
                    )
                    cur.executemany("update films set cast_top = %s where id = %s", tops)
                    cur.execute("update films set billing_checked_at = now() where id = any(%s)", (ids_,))
                conn.commit()
                done += len(group)
            log.info("billing %d/%d, %.0f films/s", done, len(todo), done / max(time.monotonic() - started, 1))
    return done


def resort_cast_top(conn) -> int:
    """Leading cast of every checked film in billing order (films checked before cast_top followed billing)."""
    rows = conn.execute(
        "select film_id, name, billing from film_people p join films f on f.id = p.film_id "
        "where p.role = 'cast' and f.billing_checked_at is not null order by film_id, ord"
    ).fetchall()
    cast: dict[str, list[tuple[str, int | None]]] = {}
    for film_id, name, billing in rows:
        cast.setdefault(film_id, []).append((name, billing))
    tops = [(top_cast([n for n, _ in people], {n: b for n, b in people if b}), f) for f, people in cast.items()]
    with conn.cursor() as cur:
        cur.executemany("update films set cast_top = %s where id = %s", tops)
    conn.commit()
    log.info("cast_top in billing order: %d films", len(tops))
    return len(tops)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--max-films", type=int, default=None)
    parser.add_argument("--resort", action="store_true", help="only re-sort the leading cast of checked films")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    from cinesense.core.config import get_settings
    from cinesense.data_sources.db import connect

    s = get_settings()
    if not s.database_url:
        raise SystemExit("SUPABASE_DB_URL is needed")
    with connect(s.database_url) as conn:
        if args.resort:
            resort_cast_top(conn)
        else:
            asyncio.run(backfill(conn, args.max_films))


if __name__ == "__main__":
    main()
