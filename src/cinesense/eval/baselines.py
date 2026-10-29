"""The two deterministic baselines from spec §7 next to CineSense, on identical hard filters.

- bayesian: filters + Bayesian rating sort (no tags, no embeddings, no profile)
- cosine: movieFinder's method, 0.7 * cosine(tag vector, weighted one-hot) + 0.3 * Bayesian rating / 5
- cinesense: the combined ranking (weighted tag relevance, plot RAG, people, rating)
"""

import statistics

import numpy as np

from cinesense.domain.criteria import MUST_THRESHOLD, NOT_THRESHOLD, SearchCriteria
from cinesense.domain.models import Movie
from cinesense.recommend.baseline import DEFAULT_PRIOR_MEAN, bayesian_rating
from cinesense.recommend.combined import _passes
from cinesense.recommend.tags import tag_match, tag_scores
from cinesense.search.service import SearchService

RANKERS = ("bayesian", "cosine", "cinesense")


def _hard_filtered(provider, c: SearchCriteria) -> list[Movie]:
    excluded = {g.lower() for g in c.exclude_genres}
    movies = [m for m in provider.list_movies() if _passes(m, c) and not any(g.lower() in excluded for g in m.genres)]
    if c.must_tags() or c.not_tags():
        allowed = {
            i
            for i, _ in provider.tag_search(
                {}, c.must_tags(), c.not_tags(), MUST_THRESHOLD, NOT_THRESHOLD, limit=100_000
            )[0]
        }
        movies = [m for m in movies if m.id in allowed]
    return movies


def _cosine_all(provider, weights: dict[int, int]) -> dict[str, float]:
    if hasattr(provider, "_vectors"):  # offline fixture
        ids = list(provider._vectors)
        return dict(zip(ids, tag_scores(weights, np.stack([provider._vectors[i] for i in ids])).tolist(), strict=True))
    user = np.zeros(1128, dtype=np.float32)
    for idx, w in weights.items():
        user[idx] = w
    with provider._conn() as conn:  # Postgres: pgvector cosine over the whole catalogue
        rows = conn.execute("select id, 1 - (tag_vector <=> %s) from films where tag_vector is not null", (user,))
        return {r[0]: float(r[1]) for r in rows.fetchall()}


def rank(name: str, provider, c: SearchCriteria, k: int = 10, embedder=None) -> list[Movie]:
    if name == "cinesense":
        return [r.movie for r in SearchService(provider, None, embedder).run(c, 0, k).items]
    movies = _hard_filtered(provider, c)
    rated = [m.ml_rating for m in movies if m.ml_rating is not None]
    prior = statistics.mean(rated) if rated else DEFAULT_PRIOR_MEAN

    def quality(m: Movie) -> float:
        return bayesian_rating(m.ml_rating, m.ml_rating_count, prior) / 5

    if name == "bayesian" or not c.prefer_weights():
        return sorted(movies, key=lambda m: (quality(m), m.ml_rating_count), reverse=True)[:k]
    cos = _cosine_all(provider, c.prefer_weights())
    scored = [(0.7 * cos[m.id] + 0.3 * quality(m), m) for m in movies if m.id in cos]
    return [m for _, m in sorted(scored, key=lambda x: x[0], reverse=True)[:k]]


def ranking_metrics(provider, c: SearchCriteria, ranked: dict[str, list[Movie]]) -> dict[str, dict]:
    weights = c.prefer_weights()
    out = {}
    for name, films in ranked.items():
        if weights and films:
            vecs = provider.tag_vectors([m.id for m in films])
            rel = float(np.mean(np.nan_to_num(tag_match(weights, vecs))))
        else:
            rel = None
        excluded = {g.lower() for g in c.exclude_genres}
        ok = [_passes(m, c) and not any(g.lower() in excluded for g in m.genres) for m in films]
        out[name] = {
            "tag_relevance": round(rel, 3) if rel is not None else None,
            "median_rating_count": int(statistics.median([m.ml_rating_count for m in films])) if films else None,
            "constraint_ok": round(sum(ok) / len(ok), 3) if ok else None,
        }
    return out
