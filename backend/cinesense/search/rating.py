"""Bayesian rating: pulls films with few MovieLens votes towards the catalogue mean."""

DEFAULT_PRIOR_MEAN = 3.5  # MovieLens scale 0–5


def bayesian_rating(rating: float | None, count: int, prior_mean: float, prior_weight: int = 200) -> float:
    """Weighted rating that pulls films with few votes towards the prior mean."""
    if rating is None or count <= 0:
        return prior_mean
    return (count * rating + prior_weight * prior_mean) / (count + prior_weight)


def catalogue_rating(rating: float | None, count: int) -> float:
    """The rating a "highly rated" filter compares: Bayesian against a fixed prior, so it does not depend on which
    other films a search happens to find."""
    return bayesian_rating(rating, count, DEFAULT_PRIOR_MEAN)
