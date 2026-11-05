"""'Highly rated': a hard filter on the Bayesian MovieLens rating, widened step by step when it finds too little."""

import pytest
from pydantic import ValidationError

from cinesense.core.criteria import SearchCriteria, TagCriterion
from cinesense.data_sources.fixture import FixtureProvider
from cinesense.search.rating import DEFAULT_PRIOR_MEAN, bayesian_rating
from cinesense.search.service import SearchService
from cinesense.search.widening import misses, relaxation_options

TAGS = [f"t{i}" for i in range(1128)]


def test_min_rating_range():
    assert SearchCriteria(min_rating=3.8).min_rating == 3.8
    with pytest.raises(ValidationError):
        SearchCriteria(min_rating=6)


def test_search_keeps_only_films_rated_at_least_min_rating():
    p = FixtureProvider()
    items = (
        SearchService(p)
        .run(SearchCriteria(tags=[TagCriterion(idx=p.list_tags().index("funny"))], min_rating=4.1))
        .items
    )
    assert items
    for r in items:
        m = r.movie
        assert bayesian_rating(m.ml_rating, m.ml_rating_count, DEFAULT_PRIOR_MEAN) >= 4.1


def test_rating_relaxation_lowers_then_drops_the_filter():
    opt = next(o for o in relaxation_options(SearchCriteria(min_rating=3.9), TAGS) if o.id == "rating")
    assert opt.criteria.min_rating == pytest.approx(3.6) and opt.label == "Rated 3.6 or better"
    last = next(o for o in relaxation_options(SearchCriteria(min_rating=3.7), TAGS) if o.id == "rating")
    assert last.criteria.min_rating is None and last.label == "Any rating"


def test_misses_name_a_lower_rating():
    from cinesense.core.models import Movie

    film = Movie.model_validate({"id": "x", "title": "X", "ml_rating": 3.4, "ml_rating_count": 50000})
    assert misses(film, SearchCriteria(min_rating=3.8), TAGS) == ["rated 3.4, below 3.8"]
