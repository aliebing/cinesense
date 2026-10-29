"""Mood-tag ranking over Tag Genome vectors (movieFinder's method, vectorised and consistent)."""

import numpy as np

from cinesense.domain.models import Movie, MovieQuery, RankedMovie
from cinesense.recommend.baseline import DEFAULT_PRIOR_MEAN, bayesian_rating
from cinesense.recommend.filters import apply_filters


def tag_scores(weights: dict[int, int], matrix: np.ndarray) -> np.ndarray:
    """movieFinder baseline: cosine of a weighted one-hot tag vector with each row; zeros if no weights."""
    n = matrix.shape[0]
    if not weights:
        return np.zeros(n, dtype=np.float32)
    user = np.zeros(matrix.shape[1], dtype=np.float32)
    for idx, w in weights.items():
        user[idx] = w
    m = np.nan_to_num(matrix)
    denom = np.linalg.norm(m, axis=1) * np.linalg.norm(user)
    with np.errstate(divide="ignore", invalid="ignore"):
        sims = np.where(denom > 0, m @ user / denom, 0.0)
    return sims.astype(np.float32)


def tag_match(weights: dict[int, int], matrix: np.ndarray) -> np.ndarray:
    """Weighted mean relevance of the requested tags only (0..1). Unlike cosine over all 1,128 tags it does
    not flatter films with a thin tag profile."""
    if not weights:
        return np.zeros(matrix.shape[0], dtype=np.float32)
    idxs = list(weights)
    w = np.asarray([weights[i] for i in idxs], dtype=np.float32)
    return (np.nan_to_num(matrix[:, idxs]) @ w / w.sum()).astype(np.float32)


def rank_by_tags(movies: list[Movie], vectors: np.ndarray, weights: dict[int, int], q: MovieQuery) -> list[RankedMovie]:
    """score = 0.7 * cosine + 0.3 * Bayesian rating / 5; the displayed percent is the same score."""
    keep = {m.id for m in apply_filters(movies, q)}
    has_vec = ~np.isnan(vectors).any(axis=1)
    sims = tag_scores(weights, vectors)
    rated = [m.ml_rating for m in movies if m.ml_rating is not None]
    prior = float(np.mean(rated)) if rated else DEFAULT_PRIOR_MEAN
    out = []
    for i, m in enumerate(movies):
        if m.id not in keep or not has_vec[i]:
            continue
        score = 0.7 * float(sims[i]) + 0.3 * bayesian_rating(m.ml_rating, m.ml_rating_count, prior) / 5
        out.append(RankedMovie(movie=m, score=score, match_percent=max(0, min(100, round(100 * score)))))
    return sorted(out, key=lambda r: r.score, reverse=True)
