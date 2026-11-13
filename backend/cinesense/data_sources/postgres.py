"""Catalogue access in Supabase Postgres (pgvector for plot embeddings and Tag Genome vectors)."""

import logging
import threading
import time
from datetime import date, timedelta

import numpy as np

from cinesense.core.billing import role_weight
from cinesense.core.models import Availability, Movie

log = logging.getLogger(__name__)

IN_CINEMA_DAYS = 56
_FIELDS = (
    "id, title, title_de, kind, year, runtime_min, original_language, genres, world_ids, top_tags, overview, "
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
        self._refreshing = False  # one background reload at a time

    # --- MovieProvider -------------------------------------------------
    def list_movies(self) -> list[Movie]:
        """The whole catalogue, cached. Once the cache is stale it is still served while a background thread
        reloads it (loading ~20,000 films takes seconds; no visitor should wait for that). Only the very first
        call waits."""
        with self._lock:
            movies = self._movies
            stale = movies is not None and time.monotonic() - self._loaded_at > self._cache_seconds
            reload_now = stale and not self._refreshing
            if reload_now:
                self._refreshing = True
        if movies is None:
            movies = self._reload()
        elif reload_now:
            threading.Thread(target=self._reload_in_background, daemon=True).start()
        return list(movies)  # shared, read-only objects; SearchService copies the page it returns

    def _reload(self) -> list[Movie]:
        with self._conn() as c:
            rows = c.execute(f"select {_FIELDS} from films").fetchall()
        movies = [row_to_movie(r) for r in rows]
        with self._lock:
            self._movies, self._by_id, self._loaded_at = movies, {m.id: m for m in movies}, time.monotonic()
        return movies

    def _reload_in_background(self) -> None:
        try:
            self._reload()
        except Exception:  # noqa: BLE001 — keep serving the old catalogue; the next call tries again
            log.exception("catalogue reload failed")
        finally:
            with self._lock:
                self._refreshing = False

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
        only_ids: list[str] | None = None,
        skip_ids: list[str] | None = None,
    ) -> tuple[list[tuple[str, float]], int]:
        """Weighted mean relevance of the requested tags, computed in Postgres, with must/not tag constraints.
        `only_ids` / `skip_ids` restrict the films before the limit (the search's hard filters, worked out in Python).

        Returns (ids with score, number of films hidden by the not-tags).
        """
        conds, params = ["true"], []
        for idx in must:
            conds.append("tv[%s] >= %s")
            params += [idx + 1, must_threshold]
        hidden_sql = " or ".join(["tv[%s] >= %s"] * len(exclude)) or "false"
        hidden_params = [p for idx in exclude for p in (idx + 1, not_threshold)]
        where = " and ".join(conds)
        scope, scope_params = "", []
        if only_ids is not None:
            scope, scope_params = " and id = any(%s)", [list(only_ids)]
        elif skip_ids:
            scope, scope_params = " and not (id = any(%s))", [list(skip_ids)]
        base = (
            "with f as (select id, ml_rating_count, tag_vector::real[] as tv from films "
            f"where tag_vector is not null{scope}) "
        )
        total = sum(weights.values())
        order = " + ".join(["%s * tv[%s]"] * len(weights)) or "0"
        order_params = [p for idx, w in weights.items() for p in (w / total, idx + 1)]
        with self._conn() as c:
            hidden = c.execute(
                base + f"select count(*) from f where {where} and ({hidden_sql})", scope_params + params + hidden_params
            ).fetchone()[0]
            sql = (
                base + f"select id, {order} as sim from f where {where} and not ({hidden_sql}) "
                "order by sim desc, ml_rating_count desc limit %s"
            )
            rows = c.execute(sql, scope_params + order_params + params + hidden_params + [limit]).fetchall()
        return [(r[0], float(r[1])) for r in rows], int(hidden)

    # --- plots (RAG) ---------------------------------------------------
    def semantic_search(
        self, query_embedding: list[float], k: int = 20, only_ids: list[str] | None = None
    ) -> list[tuple[Movie, float, str]]:
        """only_ids: rank among these films only (an exact scan; for small pools like the films in cinemas)."""
        vec = np.asarray(query_embedding, dtype=np.float32)
        with self._conn() as c:
            if only_ids is not None:
                rows = c.execute(
                    "select film_id, text, 1 - (embedding <=> %s) as sim from plot_chunks "
                    "where film_id = any(%s) order by embedding <=> %s limit %s",
                    (vec, only_ids, vec, k * 4),
                ).fetchall()
            else:
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
        def sounds(col: str) -> str:  # an input without letters sounds like nothing and must not match every title
            q_sound = "metaphone(cs_norm(%(q)s), 24)"
            return f"({q_sound} <> '' and metaphone(cs_norm({col}), 24) = {q_sound})"

        def contains(col: str) -> str:
            return f"cs_norm({col}) like '%%' || cs_norm(%(ql)s) || '%%' escape '\\'"

        def score(col: str) -> str:
            # a title that contains the query beats one that sounds alike; the closer one ranks higher
            sim = f"similarity(cs_norm({col}), cs_norm(%(q)s))"
            return (
                f"greatest({sim}, case when {sounds(col)} then 0.6 else 0 end, "
                f"case when {contains(col)} then 0.85 + 0.1 * {sim} else 0 end)"
            )

        def matches(col: str) -> str:
            return f"(cs_norm({col}) %% cs_norm(%(q)s) or {sounds(col)} or {contains(col)})"

        # the German title (live imports, from Wikidata) counts as well: "Winnetou" finds "Apache Gold"
        sql = (
            f"select id, greatest({score('title')}, coalesce({score('title_de')}, 0)) as s from films "
            f"where {matches('title')} or (title_de is not null and {matches('title_de')}) "
            "order by s desc, ml_rating_count desc limit %(limit)s"
        )
        with self._conn() as c:
            ql = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")  # "%" is a character, not "anything"
            rows = c.execute(sql, {"q": q, "ql": ql, "limit": limit}).fetchall()
        return {r[0]: max(float(r[1]), 0.5) for r in rows}

    def suggest_people(self, q: str, role: str = "any", limit: int = 8) -> list[str]:
        """Distinct names for typing suggestions: names containing the input first, then typo-close ones,
        then the better-known (more films)."""
        role_sql = "" if role == "any" else "and role = %(role)s"
        contains = "cs_norm(name) like '%%' || cs_norm(%(ql)s) || '%%' escape '\\'"
        sql = (
            f"select name, bool_or({contains}) as hit, max(word_similarity(cs_norm(%(q)s), cs_norm(name))) as ws, "
            f"count(*) as n from film_people where ({contains} or cs_norm(%(q)s) <%% cs_norm(name)) {role_sql} "
            "group by name order by hit desc, ws desc, n desc limit %(limit)s"
        )
        ql = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        with self._conn() as c:
            rows = c.execute(sql, {"q": q, "ql": ql, "role": role, "limit": limit}).fetchall()
        return [r[0] for r in rows]

    def search_person(self, q: str, role: str = "any", limit: int = 400) -> tuple[dict[str, float], dict[str, str]]:
        role_sql = "" if role == "any" else "and role = %(role)s"
        sounds = (
            "(metaphone(cs_norm(%(q)s), 24) <> '' and metaphone(cs_norm(name), 24) = metaphone(cs_norm(%(q)s), 24))"
        )
        sql = (
            "select film_id, name, greatest(similarity(cs_norm(name), cs_norm(%(q)s)), "
            f"case when {sounds} then 0.6 else 0 end) as s, role, billing "
            f"from film_people where (cs_norm(name) %% cs_norm(%(q)s) or {sounds}) "
            f"{role_sql} order by s desc limit %(limit)s"
        )
        with self._conn() as c:
            rows = c.execute(sql, {"q": q, "role": role, "limit": limit}).fetchall()
        scores: dict[str, float] = {}
        names: dict[str, str] = {}
        best = max((float(r[2]) for r in rows), default=0.0)
        for film_id, name, s, film_role, billing in rows:
            # keep only the best-matching person (a typo of one name shouldn't pull in similar names);
            # a lead or a director counts fully, a small part less
            score = float(s) * role_weight(film_role, billing)
            if float(s) >= best - 0.15 and score > scores.get(film_id, 0.0):
                scores[film_id] = score
                names[film_id] = name
        return scores, names

    def refresh(self) -> None:
        """Reload the catalogue on the next access (films were enriched in the background)."""
        with self._lock:
            self._movies = None

    # --- lazy import of live search hits ----------------------------------
    def upsert_live(self, movies: list[Movie]) -> None:
        rows = [
            (
                m.id,
                m.wikidata_id,
                m.imdb_id,
                m.kind,
                m.title,
                m.title_de,
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
                    "insert into films (id, wikidata_id, imdb_id, kind, title, title_de, year, runtime_min, genres, "
                    "directors, cast_top, world_ids, youtube_key, wikipedia_title, overview, poster_url, "
                    "horizontal_poster_url, backdrop_url) values "
                    "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "on conflict do nothing",
                    rows,
                )
            c.commit()
        with self._lock:
            self._movies = None  # new films: reload once
