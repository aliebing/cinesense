from cinesense.domain.models import MovieQuery
from cinesense.recommend.baseline import bayesian_rating, rank_baseline


def test_bayesian_pulls_low_vote_counts_to_prior():
    assert bayesian_rating(9.5, 10, prior_mean=6.5) < bayesian_rating(8.0, 20000, prior_mean=6.5)
    assert bayesian_rating(None, 0, prior_mean=6.5) == 6.5


def test_rank_baseline_sorted_with_match_percent(make_movie):
    ms = [
        make_movie(id="lo", vote_average=5.0, vote_count=5000),
        make_movie(id="hi", vote_average=8.5, vote_count=5000),
    ]
    ranked = rank_baseline(ms, MovieQuery())
    assert [r.movie.id for r in ranked] == ["hi", "lo"]
    assert 0 <= ranked[-1].match_percent <= ranked[0].match_percent <= 100


def test_rank_baseline_applies_filters_and_handles_empty(make_movie):
    ms = [make_movie(id="h", genres=["Horror"])]
    assert rank_baseline(ms, MovieQuery(exclude_genres=["Horror"])) == []
