from cinesense.search.rating import bayesian_rating


def test_bayesian_pulls_low_vote_counts_to_prior():
    assert bayesian_rating(4.9, 10, prior_mean=3.5) < bayesian_rating(4.2, 20000, prior_mean=3.5)
    assert bayesian_rating(None, 0, prior_mean=3.5) == 3.5
