"""Build the CineSense catalogue in Supabase.

    MOVIELENS_DB_PATH=/path/to/moviedoc.db uv run python -m cinesense.catalog_import.pipeline [--init-schema]

Steps: genome tags -> Tag Genome films + Wikidata (+ people) -> extras (documentaries,
German releases since 2021) -> Wikipedia plots -> chunks -> OpenRouter embeddings.
Idempotent and resumable; never calls the Streaming API.
"""

import argparse
import asyncio
import logging
import time
from datetime import date

import httpx
import numpy as np

from cinesense.catalog_import.extra_titles import fetch_recent_de_releases
from cinesense.catalog_import.languages import fetch_languages
from cinesense.catalog_import.movielens import (
    MovieLensFilm,
    read_documentaries_without_genome,
    read_films,
    read_genome_tags,
)
from cinesense.core.config import get_settings, load_env_file
from cinesense.core.worlds_map import assign_worlds, top_tags
from cinesense.data_sources.db import connect, init_schema
from cinesense.data_sources.embeddings import EmbeddingClient
from cinesense.data_sources.wikidata import (
    WikidataFilm,
    fetch_by_imdb,
    fetch_german_titles,
    fetch_people,
    fetch_wikidata,
)
from cinesense.data_sources.wikipedia import chunk_text, fetch_plot

log = logging.getLogger("cinesense.catalog_import")

FILM_COLUMNS = [
    "id",
    "movielens_id",
    "wikidata_id",
    "imdb_id",
    "kind",
    "title",
    "title_de",
    "year",
    "runtime_min",
    "original_language",
    "genres",
    "directors",
    "cast_top",
    "world_ids",
    "top_tags",
    "youtube_key",
    "release_date_de",
    "wikipedia_title",
    "ml_rating",
    "ml_rating_count",
    "tag_vector",
]


def film_row(ml: MovieLensFilm, wd: WikidataFilm, tags: list[str]) -> dict:
    top = top_tags(ml.tag_vector, tags)
    kind = "documentary" if "Documentary" in ml.genres else "film"
    return {
        "id": f"ml-{ml.movielens_id}",
        "movielens_id": ml.movielens_id,
        "wikidata_id": wd.wikidata_id,
        "imdb_id": wd.imdb_id,
        "kind": kind,
        "title": ml.title,
        "title_de": wd.title_de,
        "year": ml.year,
        "runtime_min": wd.runtime_min,
        "original_language": wd.original_language,
        "genres": ml.genres,
        "directors": wd.directors,
        "cast_top": wd.cast[:5],
        "world_ids": assign_worlds(ml.genres, top),
        "top_tags": top,
        "youtube_key": wd.youtube_key,
        "release_date_de": wd.release_date_de,
        "wikipedia_title": wd.wikipedia_title,
        "ml_rating": ml.ml_rating,
        "ml_rating_count": ml.ml_rating_count,
        "tag_vector": ml.tag_vector,
    }


def people_rows(film_id: str, wd: WikidataFilm) -> list[tuple[str, str, str, int]]:
    rows = [(film_id, n, "director", i) for i, n in enumerate(wd.directors)]
    rows += [(film_id, n, "cast", i) for i, n in enumerate(wd.cast)]
    return rows


def _upsert_films(conn, rows: list[dict]) -> None:
    cols = ", ".join(FILM_COLUMNS)
    placeholders = ", ".join(f"%({c})s" for c in FILM_COLUMNS)
    updates = ", ".join(f"{c} = excluded.{c}" for c in FILM_COLUMNS if c != "id")
    with conn.cursor() as cur:
        cur.executemany(
            f"insert into films ({cols}) values ({placeholders}) on conflict (id) do update set {updates}",
            rows,
        )
    conn.commit()


def _replace_people(conn, film_ids: list[str], rows: list[tuple]) -> None:
    with conn.cursor() as cur:
        cur.execute("delete from film_people where film_id = any(%s)", (film_ids,))
        cur.executemany("insert into film_people (film_id, name, role, ord) values (%s, %s, %s, %s)", rows)
        cur.execute("update films set billing_checked_at = null where id = any(%s)", (film_ids,))  # new cast rows
    conn.commit()


async def ingest_catalogue(conn, ml_path, limit: int | None, with_extras: bool) -> None:
    tags = read_genome_tags(ml_path)
    with conn.cursor() as cur:
        cur.executemany(
            "insert into genome_tags (idx, tag) values (%s, %s) on conflict (idx) do update set tag = excluded.tag",
            list(enumerate(tags)),
        )
    conn.commit()
    films = read_films(ml_path)
    if limit:
        films = films[:limit]
    if with_extras:
        films += read_documentaries_without_genome(ml_path)
    log.info("MovieLens: %d films to enrich", len(films))
    async with httpx.AsyncClient() as client:
        wd = await fetch_wikidata([f.movielens_id for f in films], client)
        log.info("Wikidata matches: %d", len(wd))
        await settle_languages(list(wd.values()), client)
        rows, people = [], []
        # one row per Wikidata item: MovieLens has a few duplicates; films are ordered most-rated first
        taken = dict(conn.execute("select wikidata_id, id from films where wikidata_id is not null").fetchall())
        for f in films:
            if f.movielens_id not in wd:
                continue
            qid = wd[f.movielens_id].wikidata_id
            if taken.get(qid, f"ml-{f.movielens_id}") != f"ml-{f.movielens_id}":
                continue
            taken[qid] = f"ml-{f.movielens_id}"
            if f.tag_vector is None and not wd[f.movielens_id].wikipedia_title:
                continue  # documentaries without genome need a Wikipedia article to be useful
            rows.append(film_row(f, wd[f.movielens_id], tags))
            people += people_rows(rows[-1]["id"], wd[f.movielens_id])
        for i in range(0, len(rows), 500):
            _upsert_films(conn, rows[i : i + 500])
        _replace_people(conn, [r["id"] for r in rows], people)
        log.info("Upserted %d MovieLens films, %d people rows", len(rows), len(people))
        if with_extras:
            recent = await fetch_recent_de_releases(date(2021, 1, 1), client)
            existing = {r[0] for r in conn.execute("select wikidata_id from films where wikidata_id is not null")}
            recent = [r for r in recent if r["wikidata_id"] not in existing and r["title"]]
            people = [
                p
                for r in recent
                for p in people_rows(
                    r["id"], WikidataFilm(None, r["wikidata_id"], directors=r["directors"], cast=r["cast"])
                )
            ]
            for i in range(0, len(recent), 500):
                _upsert_films(conn, recent[i : i + 500])
            _replace_people(conn, [r["id"] for r in recent], people)
            log.info("Upserted %d German releases since 2021 from Wikidata", len(recent))


async def ingest_plots(
    conn,
    embedder: EmbeddingClient | None,
    max_films: int | None,
    concurrency: int = 5,
    ids: list[str] | None = None,
) -> None:
    where = "wikipedia_title is not null and plot_checked_at is null"
    params: tuple = ()
    if ids is not None:  # lazily imported films only — never crawl the whole catalogue from an API worker
        where += " and id = any(%s)"
        params = (ids,)
    todo = conn.execute(
        f"select id, wikipedia_title from films where {where} order by ml_rating_count desc nulls last, id",
        params,
    ).fetchall()
    if max_films:
        todo = todo[:max_films]
    log.info("Plots to fetch: %d", len(todo))
    sem = asyncio.Semaphore(concurrency)
    done = without = 0
    started = time.monotonic()
    async with httpx.AsyncClient() as client:

        async def one(title: str) -> str | None:
            async with sem:
                try:
                    return await fetch_plot(title, client)
                except httpx.HTTPError as exc:
                    log.warning("plot fetch failed for %s: %s", title, exc)
                    return "__error__"

        for i in range(0, len(todo), 50):
            group = todo[i : i + 50]
            plots = await asyncio.gather(*(one(t) for _, t in group))
            chunk_rows, overview_rows, checked = [], [], []
            for (film_id, _), plot in zip(group, plots, strict=True):
                if plot == "__error__":
                    continue  # retry on next run
                checked.append(film_id)
                if not plot:
                    without += 1
                    continue
                overview_rows.append((plot.split("\n\n")[0][:700], film_id))
                chunk_rows += [(film_id, j, c) for j, c in enumerate(chunk_text(plot))]
            if embedder and chunk_rows:
                vectors = await embedder.embed([c for _, _, c in chunk_rows])
                with conn.cursor() as cur:
                    cur.executemany(
                        "insert into plot_chunks (film_id, idx, text, embedding) values (%s, %s, %s, %s) "
                        "on conflict (film_id, idx) do update "
                        "set text = excluded.text, embedding = excluded.embedding",
                        [
                            (f, j, c, np.asarray(v, dtype=np.float32))
                            for (f, j, c), v in zip(chunk_rows, vectors, strict=True)
                        ],
                    )
            with conn.cursor() as cur:
                cur.executemany("update films set overview = %s where id = %s", overview_rows)
                if embedder or not chunk_rows:
                    cur.execute("update films set plot_checked_at = now() where id = any(%s)", (checked,))
            conn.commit()
            done += len(group)
            if done % 500 < 50:
                rate = done / max(time.monotonic() - started, 1)
                log.info(
                    "plots %d/%d (%d without plot), %.1f films/s, embedding tokens %s, cost $%.4f",
                    done,
                    len(todo),
                    without,
                    rate,
                    embedder.total_tokens if embedder else 0,
                    embedder.total_cost if embedder else 0,
                )
    log.info("Plots done: %d processed, %d without plot section", done, without)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--init-schema", action="store_true")
    parser.add_argument("--no-films", action="store_true", help="skip the catalogue step")
    parser.add_argument("--no-extras", action="store_true", help="skip documentaries and recent German releases")
    parser.add_argument("--no-plots", action="store_true")
    parser.add_argument("--limit", type=int, default=None, help="only the N most-rated genome films (test runs)")
    parser.add_argument("--plots", type=int, default=None, help="only N plots this run")
    parser.add_argument("--enrich-live", action="store_true", help="link live imports to Wikidata, load their plots")
    parser.add_argument("--german-titles", action="store_true", help="German titles from Wikidata for the catalogue")
    parser.add_argument("--languages", action="store_true", help="recheck original languages (country of origin)")
    parser.add_argument("--people", action="store_true", help="reload directors and cast from Wikidata where changed")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_env_file()
    s = get_settings()
    if not s.database_url:
        raise SystemExit("SUPABASE_DB_URL is not set")
    if args.init_schema:
        init_schema(s.database_url)
        log.info("Schema ready")
    if args.enrich_live:
        enrich_new_films(None)
    if args.german_titles:
        with connect(s.database_url) as conn:
            asyncio.run(backfill_german_titles(conn))
    if args.languages:
        with connect(s.database_url) as conn:
            asyncio.run(backfill_languages(conn))
    if args.people:
        with connect(s.database_url) as conn:
            asyncio.run(refresh_people(conn))
    with connect(s.database_url) as conn:
        if not args.no_films:
            if not s.movielens_db_path:
                raise SystemExit("MOVIELENS_DB_PATH is not set")
            asyncio.run(ingest_catalogue(conn, s.movielens_db_path, args.limit, not args.no_extras))
        if not args.no_plots:
            embedder = EmbeddingClient(s.openrouter_api_key) if s.openrouter_api_key else None
            asyncio.run(ingest_plots(conn, embedder, args.plots))
            if embedder:
                log.info("Embedding usage: %d tokens, $%.4f", embedder.total_tokens, embedder.total_cost)


def people_changes(
    current_cast: dict[str, list[str]], current_directors: dict[str, list[str]], fetched: dict[str, WikidataFilm]
) -> list[str]:
    """Films whose cast or directors on Wikidata differ from ours. A film with no names back (an outage, a
    removed entry) keeps what it has."""
    return [
        film_id
        for film_id, wd in fetched.items()
        if (wd.cast or wd.directors)
        and (wd.cast != current_cast.get(film_id, []) or wd.directors != current_directors.get(film_id, []))
    ]


async def refresh_people(conn) -> list[str]:
    """Reload directors and cast from Wikidata for every film with a Wikidata id, and replace them where they
    changed (people with only a 'mul' label were missing). Changed films get their billing checked again."""
    films = conn.execute("select id, wikidata_id from films where wikidata_id is not null").fetchall()
    cast: dict[str, list[str]] = {}
    directors: dict[str, list[str]] = {}
    for film_id, name, role in conn.execute("select film_id, name, role from film_people order by film_id, role, ord"):
        (cast if role == "cast" else directors).setdefault(film_id, []).append(name)
    async with httpx.AsyncClient(timeout=120) as client:
        by_qid = await fetch_people([q for _, q in films], client)
    fetched = {film_id: by_qid[q] for film_id, q in films if q in by_qid}
    changed = people_changes(cast, directors, fetched)
    for i in range(0, len(changed), 500):
        ids = changed[i : i + 500]
        _replace_people(conn, ids, [r for f in ids for r in people_rows(f, fetched[f])])
        with conn.cursor() as cur:
            cur.executemany(
                "update films set directors = %s, cast_top = %s where id = %s",
                [(fetched[f].directors, fetched[f].cast[:5], f) for f in ids],
            )
        conn.commit()
    log.info("People: %d of %d films updated (%d answered by Wikidata)", len(changed), len(films), len(fetched))
    return changed


async def backfill_german_titles(conn) -> int:
    """German titles from Wikidata for every film that has a Wikidata id but no German title yet (one-off; new
    catalogue ingests fetch them directly)."""
    todo = conn.execute(
        "select id, wikidata_id from films where title_de is null and wikidata_id is not null"
    ).fetchall()
    async with httpx.AsyncClient() as client:
        found = await fetch_german_titles([q for _, q in todo], client)
    rows = [(found[q], film_id) for film_id, q in todo if q in found]
    with conn.cursor() as cur:
        cur.executemany("update films set title_de = %s where id = %s and title_de is null", rows)
    conn.commit()
    log.info("German titles: %d of %d films", len(rows), len(todo))
    return len(rows)


async def settle_languages(films: list[WikidataFilm], client) -> None:
    """Of several original languages, keep the primary one (see cinesense.catalog_import.languages)."""
    settled = await fetch_languages([f.wikidata_id for f in films], client)
    for f in films:
        f.original_language = settled.get(f.wikidata_id, f.original_language)


async def backfill_languages(conn) -> list[tuple[str, str | None, str]]:
    """Recheck the original language of every film with a Wikidata id (the first ingest took whichever of several
    languages came first: Life Is Beautiful was German). Returns (film id, old, new) for each change."""
    todo = conn.execute("select id, wikidata_id, original_language from films where wikidata_id is not null").fetchall()
    async with httpx.AsyncClient() as client:
        settled = await fetch_languages([q for _, q, _ in todo], client)
    changes = [(film_id, old, settled[q]) for film_id, q, old in todo if settled.get(q) and settled[q] != old]
    with conn.cursor() as cur:
        cur.executemany("update films set original_language = %s where id = %s", [(new, i) for i, _, new in changes])
    conn.commit()
    log.info("Original language: %d of %d films corrected", len(changes), len(todo))
    return changes


async def link_wikidata(conn, ids: list[str] | None = None) -> int:
    """Films imported live carry only an IMDb id. Look them up in Wikidata for the German title (searchable),
    the English Wikipedia article (for the plot), the official trailer and the original language.
    `ids=None`: every live import not linked yet (the one-off backfill)."""
    where = "id like 'imdb-%%' and wikidata_id is null and imdb_id is not null"
    params: tuple = ()
    if ids is not None:
        where += " and id = any(%s)"
        params = (ids,)
    todo = dict(conn.execute(f"select id, imdb_id from films where {where}", params).fetchall())
    if not todo:
        return 0
    async with httpx.AsyncClient() as client:
        found = await fetch_by_imdb(list(todo.values()), client)
        await settle_languages(list(found.values()), client)
    linked = 0
    for film_id, imdb in todo.items():
        wd = found.get(imdb)
        if wd is None:
            continue
        # wikidata_id is unique: an item the catalogue already holds (as ml-…) is left on that film
        conn.execute(
            "update films set wikidata_id = case when exists (select 1 from films f where f.wikidata_id = %s) "
            "then wikidata_id else %s end, title_de = coalesce(title_de, %s), "
            "wikipedia_title = coalesce(wikipedia_title, %s), youtube_key = coalesce(youtube_key, %s), "
            "original_language = coalesce(original_language, %s) where id = %s",
            (wd.wikidata_id, wd.wikidata_id, wd.title_de, wd.wikipedia_title, wd.youtube_key,
             wd.original_language, film_id),
        )  # fmt: skip
        linked += 1
    conn.commit()
    log.info("Linked %d of %d live imports to Wikidata", linked, len(todo))
    return linked


def enrich_new_films(ids: list[str] | None) -> None:
    """Background task for lazily imported films: Wikidata link (German title, Wikipedia article, trailer), then
    plots, chunks and embeddings. `ids=None` enriches every live import not linked yet."""
    load_env_file()
    s = get_settings()
    if not s.database_url or ids == []:
        return
    embedder = EmbeddingClient(s.openrouter_api_key) if s.openrouter_api_key else None
    with connect(s.database_url) as conn:
        asyncio.run(link_wikidata(conn, ids))
        if ids is None:  # the films the backfill just linked
            ids = [r[0] for r in conn.execute("select id from films where id like 'imdb-%%'").fetchall()]
        asyncio.run(ingest_plots(conn, embedder, None, ids=ids))


if __name__ == "__main__":
    main()
