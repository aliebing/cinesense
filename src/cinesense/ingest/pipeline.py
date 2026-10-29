"""Build the CineSense catalogue in Supabase.

    MOVIELENS_DB_PATH=/path/to/moviedoc.db uv run python -m cinesense.ingest.pipeline [--init-schema]

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

from cinesense.config import get_settings, load_env_file
from cinesense.db import connect, init_schema
from cinesense.ingest.embeddings import EmbeddingClient
from cinesense.ingest.extra_titles import fetch_recent_de_releases
from cinesense.ingest.movielens import (
    MovieLensFilm,
    read_documentaries_without_genome,
    read_films,
    read_genome_tags,
)
from cinesense.ingest.wikidata import WikidataFilm, fetch_wikidata
from cinesense.ingest.wikipedia import chunk_text, fetch_plot
from cinesense.ingest.worlds_map import assign_worlds, top_tags

log = logging.getLogger("cinesense.ingest")

FILM_COLUMNS = [
    "id",
    "movielens_id",
    "wikidata_id",
    "imdb_id",
    "kind",
    "title",
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
    conn.commit()


async def ingest_catalogue(conn, ml_path, limit: int | None, with_extras: bool) -> None:
    tags = read_genome_tags(ml_path)
    with conn.cursor() as cur:
        cur.executemany(
            "insert into genome_tags (idx, tag) values (%s, %s) "
            "on conflict (idx) do update set tag = excluded.tag",
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
        rows, people = [], []
        for f in films:
            if f.movielens_id not in wd:
                continue
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
            existing = {
                r[0] for r in conn.execute("select wikidata_id from films where wikidata_id is not null")
            }
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
    conn, embedder: EmbeddingClient | None, max_films: int | None, concurrency: int = 5
) -> None:
    todo = conn.execute(
        "select id, wikipedia_title from films where wikipedia_title is not null and plot_checked_at is null "
        "order by ml_rating_count desc nulls last, id"
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
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--init-schema", action="store_true")
    parser.add_argument("--no-films", action="store_true", help="skip the catalogue step")
    parser.add_argument(
        "--no-extras", action="store_true", help="skip documentaries and recent German releases"
    )
    parser.add_argument("--no-plots", action="store_true")
    parser.add_argument(
        "--limit", type=int, default=None, help="only the N most-rated genome films (test runs)"
    )
    parser.add_argument("--plots", type=int, default=None, help="only N plots this run")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_env_file()
    s = get_settings()
    if not s.database_url:
        raise SystemExit("SUPABASE_DB_URL is not set")
    if args.init_schema:
        init_schema(s.database_url)
        log.info("Schema ready")
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


if __name__ == "__main__":
    main()
