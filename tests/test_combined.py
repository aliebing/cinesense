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


class FakeProvider:
    def __init__(self, movies):
        self.movies = movies
        self.inserted = []

    def list_tags(self):
        return []

    def list_movies(self):
        return list(self.movies)

    def search_title(self, q, limit=200):
        return {}

    def search_person(self, q, role="any", limit=400):
        return {}, {}

    def tag_vectors(self, ids):
        import numpy as np

        return np.zeros((len(ids), 1128))

    def upsert_live(self, movies):
        self.inserted += movies
        self.movies += [m for m in movies if m.id not in {x.id for x in self.movies}]


class FakeLive:
    def __init__(self, movie):
        self.movie = movie
        self.calls = 0

    def search_title(self, q):
        self.calls += 1
        return [self.movie]

    def search_person(self, q):
        self.calls += 1
        return q, [self.movie]


def test_extended_runs_when_local_below_5_and_inserts_lazily(make_movie):
    from cinesense.search.service import SearchService

    new = make_movie(id="imdb-tt1", title="Brand New Film")
    prov, live = FakeProvider([make_movie(id="a")]), FakeLive(new)
    res = SearchService(prov, live=live).run(SearchCriteria(title="brand new"), 0, 20)
    assert live.calls == 1 and res.extended_used
    assert [m.id for m in prov.inserted] == ["imdb-tt1"]
    assert any(r.movie.id == "imdb-tt1" for r in res.items)


def test_extended_not_used_without_title_or_person(make_movie):
    from cinesense.search.service import SearchService

    live = FakeLive(make_movie(id="x"))
    res = SearchService(FakeProvider([make_movie(id="a")]), live=live).run(SearchCriteria(extended=True), 0, 20)
    assert live.calls == 0 and not res.extended_used


def test_extended_skipped_on_later_pages(make_movie):
    from cinesense.search.service import SearchService

    live = FakeLive(make_movie(id="x"))
    SearchService(FakeProvider([make_movie(id="a")]), live=live).run(SearchCriteria(title="brand new"), 20, 20)
    assert live.calls == 0


def test_profile_reasons_stay_linear(make_movie):
    import time

    from cinesense.domain.criteria import SearchCriteria
    from cinesense.recommend.combined import Signals, combined_rank

    movies = [make_movie(id=f"m{i}", title=f"F{i}") for i in range(5000)]
    sig = Signals(profile={f"m{i}": (i % 100) / 100 for i in range(3000)})
    t0 = time.perf_counter()
    res = combined_rank(movies, SearchCriteria(), sig, limit=5000)
    assert time.perf_counter() - t0 < 1.0
    assert sum("fits your taste" in r.reasons for r in res.items) == 750


class FakeStreaming:
    def __init__(self, streaming_ids):
        self.streaming_ids = streaming_ids
        self.lookups = []

    def get_de(self, imdb_id):
        from cinesense.domain.models import StreamingOption

        self.lookups.append(imdb_id)
        return [StreamingOption(service="Netflix", type="subscription")] if imdb_id in self.streaming_ids else []


def test_stream_filter_fills_the_page_from_further_candidates(make_movie):
    """The best few films often don't stream: a short page must not come back empty while others do."""
    from cinesense.search.service import SearchService

    movies = [make_movie(id=f"m{i}", imdb_id=f"tt{i}", ml_rating=4.5 - i / 5) for i in range(6)]
    streaming = FakeStreaming({"tt3", "tt5"})
    res = SearchService(FakeProvider(movies), streaming=streaming).run(SearchCriteria(availability="stream"), 0, 1)
    assert [r.movie.id for r in res.items] == ["m3"]
    assert streaming.lookups == ["tt0", "tt1", "tt2", "tt3"]  # stops once the page is full
    assert res.total == 3  # the three known non-streamers no longer count
