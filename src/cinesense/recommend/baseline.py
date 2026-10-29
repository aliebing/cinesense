from statistics import mean

from cinesense.domain.models import Movie, MovieQuery, RankedMovie
from cinesense.recommend.filters import apply_filters

DEFAULT_PRIOR_MEAN = 3.5  # MovieLens scale 0–5


def bayesian_rating(rating: float | None, count: int, prior_mean: float, prior_weight: int = 200) -> float:
    """Weighted rating that pulls films with few votes towards the prior mean."""
    if rating is None or count <= 0:
        return prior_mean
    return (count * rating + prior_weight * prior_mean) / (count + prior_weight)


def rank_baseline(movies: list[Movie], q: MovieQuery) -> list[RankedMovie]:
    """Baseline for evaluation: hard filters, then sort by Bayesian MovieLens rating only."""
    candidates = apply_filters(movies, q)
    rated = [m.ml_rating for m in candidates if m.ml_rating is not None]
    prior = mean(rated) if rated else DEFAULT_PRIOR_MEAN
    ranked = []
    for m in candidates:
        score = bayesian_rating(m.ml_rating, m.ml_rating_count, prior)
        ranked.append(RankedMovie(movie=m, score=score, match_percent=max(0, min(100, round(20 * score)))))
    return sorted(ranked, key=lambda r: r.score, reverse=True)
