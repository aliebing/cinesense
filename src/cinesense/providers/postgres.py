"""Catalogue access in Supabase Postgres (pgvector for plot embeddings and Tag Genome vectors)."""

import threading
import time
from datetime import date, timedelta

import numpy as np

from cinesense.domain.models import Availability, Movie

IN_CINEMA_DAYS = 56
_FIELDS = (
    "id, title, kind, year, runtime_min, original_language, genres, world_ids, top_tags, overview, "
    "directors, cast_top, movielens_id, imdb_id, wikidata_id, wikipedia_title, release_date_de, poster_url, "
    "horizontal_poster_url, backdrop_url, youtube_key, ml_rating, ml_rating_count"
)
_NAMES = [f.strip() for f in _FIELDS.split(",")] + ["images_checked"]
_FIELDS += ", (images_fetched_at is not null) as images_checked"


def row_to_movie(row: tuple) -> Movie:
    d = dict(zip(_NAMES, row, strict=True))
    rel: date | None = d["release_date_de"]
    in_cinema = bool(rel and date.today() - timedelta(days=IN_CINEMA_DAYS) <= rel <= date.today())
    return Movie(**d, availability=Availability(in_cinema_de=in_cinema))


class PostgresProvider:
    def __init__(self, conn_factory, cache_seconds: int = 600) -> None:
        self._conn = conn_factory
        self._cache_seconds = cache_seconds
        self._movies: list[Movie] | None = None
        self._by_id: dict[str, Movie] = {}
        self._loaded_at = 0.0
        self._tags: list[str] | None = None
        self._mean: np.ndarray | None = None
        self._lock = threading.Lock()

    # --- MovieProvider -------------------------------------------------
    def list_movies(self) -> list[Movie]:
        with self._lock:
            movies = self._movies
            fresh = movies is not None and time.monotonic() - self._loaded_at <= self._cache_seconds
        if not fresh:
            with self._conn() as c:
                rows = c.execute(f"select {_FIELDS} from films").fetchall()
            movies = [row_to_movie(r) for r in rows]
            with self._lock:
                self._movies, self._by_id, self._loaded_at = (
                    movies,
                    {m.id: m for m in movies},
                    time.monotonic(),
                )
        return list(movies)  # shared, read-only objects; SearchService copies the page it returns

    def get_movie(self, movie_id: str) -> Movie | None:
        with self._conn() as c:
            row = c.execute(f"select {_FIELDS} from films where id = %s", (movie_id,)).fetchone()
        return row_to_movie(row) if row else None

    def get_many(self, ids: list[str]) -> list[Movie]:
        if not ids:
            return []
        with self._conn() as c:
            rows = c.execute(f"select {_FIELDS} from films where id = any(%s)", (ids,)).fetchall()
        by_id = {r[0]: row_to_movie(r) for r in rows}
        return [by_id[i] for i in ids if i in by_id]

    def update_images(self, movie_id: str, poster: str | None, horizontal: str | None, backdrop: str | None) -> None:
        """Store looked-up images (or just 'checked' if none were found)."""
        with self._conn() as c:
            c.execute(
                "update films set poster_url = coalesce(%s, poster_url), "
                "horizontal_poster_url = coalesce(%s, horizontal_poster_url), "
                "backdrop_url = coalesce(%s, backdrop_url), images_fetched_at = now() where id = %s",
                (poster, horizontal, backdrop, movie_id),
            )
            c.commit()
        with self._lock:  # patch the cached film; never reload the whole table for an image update
            m = self._by_id.get(movie_id)
            if m is not None:
                m.poster_url = m.poster_url or poster
                m.horizontal_poster_url = m.horizontal_poster_url or horizontal
                m.backdrop_url = m.backdrop_url or backdrop
                m.images_checked = True

    # --- tags ------------------------------------------------------------
    def list_tags(self) -> list[str]:
        if self._tags is None:
            with self._conn() as c:
                self._tags = [r[0] for r in c.execute("select tag from genome_tags order by idx")]
        return list(self._tags)

    def tag_vectors(self, ids: list[str]) -> np.ndarray:
        with self._conn() as c:
            rows = dict(c.execute("select id, tag_vector from films where id = any(%s)", (ids,)).fetchall())
        out = np.full((len(ids), 1128), np.nan, dtype=np.float32)
        for i, film_id in enumerate(ids):
            v = rows.get(film_id)
            if v is not None:
                out[i] = np.asarray(v.to_numpy() if hasattr(v, "to_numpy") else v, dtype=np.float32)
        return out

    def mean_tag_vector(self) -> np.ndarray:
        if self._mean is None:
            with self._conn() as c:
                v = c.execute("select avg(tag_vector) from films where tag_vector is not null").fetchone()[0]
            self._mean = np.asarray(v.to_numpy() if hasattr(v, "to_numpy") else v, dtype=np.float32)
        return self._mean

    def tag_search(
        self,
        weights: dict[int, int],
        must: list[int],
        exclude: list[int],
        must_threshold: float = 0.6,
        not_threshold: float = 0.5,
        limit: int = 500,
    ) -> tuple[list[tuple[str, float]], int]:
        """Weighted mean relevance of the requested tags, computed in Postgres, with must/not tag constraints.

        Returns (ids with score, number of films hidden by the not-tags).
        """
        conds, params = ["true"], []
        for idx in must:
            conds.append("tv[%s] >= %s")
            params += [idx + 1, must_threshold]
        hidden_sql = " or ".join(["tv[%s] >= %s"] * len(exclude)) or "false"
        hidden_params = [p for idx in exclude for p in (idx + 1, not_threshold)]
        where = " and ".join(conds)
        base = (
            "with f as (select id, ml_rating_count, tag_vector::real[] as tv from films where tag_vector is not null) "
        )
        total = sum(weights.values())
        order = " + ".join(["%s * tv[%s]"] * len(weights)) or "0"
        order_params = [p for idx, w in weights.items() for p in (w / total, idx + 1)]
        with self._conn() as c:
            hidden = c.execute(
                base + f"select count(*) from f where {where} and ({hidden_sql})", params + hidden_params
            ).fetchone()[0]
            sql = (
                base + f"select id, {order} as sim from f where {where} and not ({hidden_sql}) "
                "order by sim desc, ml_rating_count desc limit %s"
            )
            rows = c.execute(sql, order_params + params + hidden_params + [limit]).fetchall()
        return [(r[0], float(r[1])) for r in rows], int(hidden)

    # --- plots (RAG) ---------------------------------------------------
    def semantic_search(self, query_embedding: list[float], k: int = 20) -> list[tuple[Movie, float, str]]:
        vec = np.asarray(query_embedding, dtype=np.float32)
        with self._conn() as c:
            c.execute("set local hnsw.ef_search = 400")  # default 40 caps HNSW recall at ~40 chunks
            rows = c.execute(
                "select film_id, text, 1 - (embedding <=> %s) as sim from plot_chunks "
                "order by embedding <=> %s limit %s",
                (vec, vec, k * 4),
            ).fetchall()
        best: dict[str, tuple[float, str]] = {}
        for film_id, text, sim in rows:
            if film_id not in best:
                best[film_id] = (float(sim), text)
        ids = list(best)[:k]
        return [(m, best[m.id][0], best[m.id][1]) for m in self.get_many(ids)]

    # --- title / people (typo, accent and sound-alike tolerant) ----------
    def search_title(self, q: str, limit: int = 200) -> dict[str, float]:
        sounds = "metaphone(cs_norm(title), 24) = metaphone(cs_norm(%(q)s), 24)"
        sql = (
            "select id, greatest(similarity(cs_norm(title), cs_norm(%(q)s)), "
            f"case when {sounds} then 0.6 else 0 end) as s "
            f"from films where cs_norm(title) %% cs_norm(%(q)s) or {sounds} "
            "or cs_norm(title) like '%%' || cs_norm(%(q)s) || '%%' "
            "order by s desc, ml_rating_count desc limit %(limit)s"
        )
        with self._conn() as c:
            rows = c.execute(sql, {"q": q, "limit": limit}).fetchall()
        return {r[0]: max(float(r[1]), 0.5) for r in rows}

    def search_person(self, q: str, role: str = "any", limit: int = 400) -> tuple[dict[str, float], dict[str, str]]:
        role_sql = "" if role == "any" else "and role = %(role)s"
        sounds = "metaphone(cs_norm(name), 24) = metaphone(cs_norm(%(q)s), 24)"
        sql = (
            "select film_id, name, greatest(similarity(cs_norm(name), cs_norm(%(q)s)), "
            f"case when {sounds} then 0.6 else 0 end) as s "
            f"from film_people where (cs_norm(name) %% cs_norm(%(q)s) or {sounds}) "
            f"{role_sql} order by s desc limit %(limit)s"
        )
        with self._conn() as c:
            rows = c.execute(sql, {"q": q, "role": role, "limit": limit}).fetchall()
        scores: dict[str, float] = {}
        names: dict[str, str] = {}
        best = max((float(r[2]) for r in rows), default=0.0)
        for film_id, name, s in rows:
            # keep only the best-matching person (a typo of one name shouldn't pull in similar names)
            if float(s) >= best - 0.15 and film_id not in scores:
                scores[film_id] = float(s)
                names[film_id] = name
        return scores, names

    # --- lazy import of live search hits ----------------------------------
    def upsert_live(self, movies: list[Movie]) -> None:
        rows = [
            (
                m.id,
                m.wikidata_id,
                m.imdb_id,
                m.kind,
                m.title,
                m.year,
                m.runtime_min,
                m.genres,
                m.directors,
                m.cast_top,
                m.world_ids,
                m.youtube_key,
                m.wikipedia_title,
                m.overview,
                m.poster_url,
                m.horizontal_poster_url,
                m.backdrop_url,
            )
            for m in movies
        ]
        with self._conn() as c:
            with c.cursor() as cur:
                cur.executemany(
                    "insert into films (id, wikidata_id, imdb_id, kind, title, year, runtime_min, genres, "
                    "directors, cast_top, world_ids, youtube_key, wikipedia_title, overview, poster_url, "
                    "horizontal_poster_url, backdrop_url) values "
                    "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "on conflict do nothing",
                    rows,
                )
            c.commit()
        with self._lock:
            self._movies = None  # new films: reload once
