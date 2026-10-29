from cinesense.domain.criteria import SearchCriteria, TagCriterion
from cinesense.recommend.combined import Signals, combined_rank


def test_combined_rank_uses_only_active_signals(make_movie):
    movies = [
        make_movie(id="a", ml_rating=4.5, ml_rating_count=9000),
        make_movie(id="b", ml_rating=2.0, ml_rating_count=50),
    ]
    sig = Signals(person={"b": 1.0, "a": 0.4})
    res = combined_rank(movies, SearchCriteria(person="x"), sig)
    assert [r.movie.id for r in res.items] == ["b", "a"]  # person dominates, rating only a tie-breaker


def test_combined_rank_excludes_genres_and_counts_hidden(make_movie):
    movies = [make_movie(id="a", genres=["Horror"]), make_movie(id="b", genres=["Comedy"])]
    res = combined_rank(movies, SearchCriteria(exclude_genres=["horror"]), Signals(), hidden_by_tags=3)
    assert [r.movie.id for r in res.items] == ["b"]
    assert res.hidden_by_exclusion == 4  # 3 by not-tags + 1 by genre
    assert res.total == 1


def test_reasons_list_matching_signals(make_movie):
    m = make_movie(id="a", cast_top=["Sandra Hüller"])
    crit = SearchCriteria(tags=[TagCriterion(idx=0, weight=8)], person="Sandra Hueller", plot_query="lonely")
    sig = Signals(
        tags={"a": 0.3},
        plot={"a": (0.6, "An astronaut lives alone on a station orbiting a distant planet for years.")},
        person={"a": 0.9},
        tag_relevance={"a": {0: 0.91}},
        tag_names={0: "dark"},
        person_names={"a": "Sandra Hüller"},
    )
    reasons = combined_rank([m], crit, sig).items[0].reasons
    assert "dark 91%" in reasons
    assert any(r.startswith("plot: An astronaut") for r in reasons)
    assert "with Sandra Hüller" in reasons


def test_tag_scores_normalised_to_best(make_movie):
    movies = [make_movie(id="a"), make_movie(id="b")]
    crit = SearchCriteria(tags=[TagCriterion(idx=0)])
    res = combined_rank(movies, crit, Signals(tags={"a": 0.12, "b": 0.06}))
    assert res.items[0].movie.id == "a" and res.items[0].match_percent >= res.items[1].match_percent


def test_paging_offset_limit(make_movie):
    movies = [make_movie(id=f"m{i}", ml_rating=3 + i / 100, ml_rating_count=1000) for i in range(30)]
    page = combined_rank(movies, SearchCriteria(), Signals(), offset=10, limit=5)
    assert page.total == 30 and len(page.items) == 5
