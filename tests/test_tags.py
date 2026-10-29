import numpy as np

from cinesense.domain.models import MovieQuery
from cinesense.recommend.tags import rank_by_tags, tag_scores


def test_tag_scores_zero_weights_no_nan():
    m = np.random.default_rng(0).random((5, 10)).astype(np.float32)
    s = tag_scores({}, m)
    assert s.shape == (5,) and not np.isnan(s).any() and (s == 0).all()


def test_tag_scores_prefers_matching_rows():
    m = np.full((3, 10), 0.05, dtype=np.float32)
    m[1, 3] = 0.95
    m[2, 7] = 0.95
    s = tag_scores({3: 10}, m)
    assert s.argmax() == 1


def test_rank_by_tags_order_matches_percent(make_movie):
    movies = [make_movie(id=f"m{i}", ml_rating=3.5, ml_rating_count=1000) for i in range(3)]
    m = np.full((3, 10), 0.05, dtype=np.float32)
    m[2, 4] = 0.9
    m[0, 4] = 0.5
    ranked = rank_by_tags(movies, m, {4: 8}, MovieQuery())
    assert [r.movie.id for r in ranked] == ["m2", "m0", "m1"]
    pct = [r.match_percent for r in ranked]
    assert pct == sorted(pct, reverse=True)


def test_rank_by_tags_skips_null_vectors(make_movie):
    movies = [make_movie(id="a"), make_movie(id="b")]
    m = np.array([[0.9, 0.1], [np.nan, np.nan]], dtype=np.float32)
    ranked = rank_by_tags(movies, m, {0: 5}, MovieQuery())
    assert [r.movie.id for r in ranked] == ["a"]
