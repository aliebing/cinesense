from statistics import mean

from cinesense.domain.models import Movie, MovieQuery, RankedMovie
from cinesense.recommend.filters import apply_filters

DEFAULT_PRIOR_MEAN = 6.5


def bayesian_rating(
    vote_average: float | None, vote_count: int, prior_mean: float, prior_weight: int = 500
) -> float:
    """Weighted rating that pulls films with few votes towards the prior mean."""
    if vote_average is None or vote_count <= 0:
        return prior_mean
    return (vote_count * vote_average + prior_weight * prior_mean) / (vote_count + prior_weight)


def rank_baseline(movies: list[Movie], q: MovieQuery) -> list[RankedMovie]:
    """Baseline for evaluation: hard filters, then sort by Bayesian TMDB rating only."""
    candidates = apply_filters(movies, q)
    rated = [m.vote_average for m in candidates if m.vote_average is not None]
    prior = mean(rated) if rated else DEFAULT_PRIOR_MEAN
    ranked = []
    for m in candidates:
        score = bayesian_rating(m.vote_average, m.vote_count, prior)
        ranked.append(RankedMovie(movie=m, score=score, match_percent=max(0, min(100, round(10 * score)))))
    return sorted(ranked, key=lambda r: r.score, reverse=True)
