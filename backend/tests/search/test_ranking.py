import pytest

from cinesense.core.criteria import SearchCriteria, TagCriterion
from cinesense.search.ranking import Signals, combined_rank


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


def test_combined_rank_counts_matches_per_floor_over_every_film_not_just_the_page(make_movie):
    """The search page picks the floor of its grid from these counts (60%, higher above 500 films, 50% if few)."""
    movies = [make_movie(id=f"m{i}", ml_rating=4.0, ml_rating_count=1000) for i in range(6)]
    tags = {"m0": 0.95, "m1": 0.85, "m2": 0.75, "m3": 0.65, "m4": 0.55, "m5": 0.1}
    crit = SearchCriteria(tags=[TagCriterion(idx=0, weight=8)])
    res = combined_rank(movies, crit, Signals(tags=tags), limit=2)
    assert len(res.items) == 2
    percents = [r.match_percent for r in combined_rank(movies, crit, Signals(tags=tags), limit=10).items]
    assert res.match_counts == {f: sum(p >= f for p in percents) for f in (50, 60, 70, 80, 90)}
    assert res.match_counts[50] > res.match_counts[90]


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

    from cinesense.core.criteria import SearchCriteria
    from cinesense.search.ranking import Signals, combined_rank

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
        from cinesense.core.models import StreamingOption

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


def test_newer_film_wins_a_tie_but_not_a_clearly_better_match(make_movie):
    old, new = make_movie(id="old", year=1975), make_movie(id="new", year=2018)
    tie = combined_rank([old, new], SearchCriteria(), Signals(), offset=0, limit=2)
    assert [r.movie.id for r in tie.items] == ["new", "old"]
    better = combined_rank([old, new], SearchCriteria(), Signals(tags={"old": 0.9, "new": 0.5}), offset=0, limit=2)
    assert [r.movie.id for r in better.items] == ["old", "new"]


def test_a_well_known_classic_beats_an_unknown_new_film(make_movie):
    classic = make_movie(id="classic", year=1986, ml_rating=4.1, ml_rating_count=3670)
    unknown = make_movie(id="unknown", year=2021, ml_rating=None, ml_rating_count=0)
    res = combined_rank([unknown, classic], SearchCriteria(), Signals(), offset=0, limit=2)
    assert [r.movie.id for r in res.items] == ["classic", "unknown"]


def test_a_title_search_gives_no_bonus_for_newer_films(make_movie):
    old = make_movie(id="old", year=1963, ml_rating=None, ml_rating_count=0)
    new = make_movie(id="new", year=2016, ml_rating=None, ml_rating_count=0)
    sig = Signals(title={"old": 0.9, "new": 0.88})
    res = combined_rank([new, old], SearchCriteria(title="Winnetou"), sig)
    assert [r.movie.id for r in res.items] == ["old", "new"]  # the closer title wins, not the newer film


def test_a_title_search_drops_sound_alikes_when_titles_contain_the_query(make_movie):
    from cinesense.search.service import SearchService

    class Prov(FakeProvider):
        def search_title(self, q, limit=200):
            return {"winnetou1": 0.9, "winwin": 0.6, "wind": 0.6}

    movies = [make_movie(id=i, title=i) for i in ("winnetou1", "winwin", "wind")]
    res = SearchService(Prov(movies)).run(SearchCriteria(title="Winnetou"), 0, 20)
    assert [r.movie.id for r in res.items] == ["winnetou1"]


def test_a_title_search_keeps_sound_alikes_when_nothing_better_matches(make_movie):
    from cinesense.search.service import SearchService

    class Prov(FakeProvider):
        def search_title(self, q, limit=200):
            return {"incep": 0.6}

    res = SearchService(Prov([make_movie(id="incep", title="Inception")])).run(SearchCriteria(title="Incepshun"), 0, 20)
    assert [r.movie.id for r in res.items] == ["incep"]  # a typo still finds the film


def test_each_genre_exclusion_counts_the_films_it_hides(make_movie):
    movies = [
        make_movie(id="a", genres=["Horror"]),
        make_movie(id="b", genres=["Horror", "Comedy"]),
        make_movie(id="c"),
    ]
    res = combined_rank(movies, SearchCriteria(exclude_genres=["Horror", "Western"]), Signals())
    assert res.hidden_by == {"genre:Horror": 2, "genre:Western": 0}


def test_the_tag_part_is_absolute_a_half_fitting_film_is_not_shown_as_a_full_match(make_movie):
    """A film that fits the mood only partly keeps that in its match, even when it is the best of the results."""
    c = SearchCriteria(tags=[TagCriterion(idx=0, weight=6)])
    film = [make_movie(id="a")]
    half = combined_rank(film, c, Signals(tags={"a": 0.6})).items[0].score
    full = combined_rank(film, c, Signals(tags={"a": 1.0})).items[0].score
    from cinesense.search.ranking import WEIGHTS

    total = WEIGHTS["tags"] + WEIGHTS["rating"] + WEIGHTS["popularity"] + WEIGHTS["recency"]
    assert abs((full - half) - WEIGHTS["tags"] * 0.4 / total) < 1e-9


def test_a_wanted_person_filters_but_gives_no_points_a_small_part_halves_the_match(make_movie):
    """Every film of a person search has that person: points for it would lift a humourless action film over the
    bar for 'Stallone + funny'. The match is the mood; a cameo (role weight 0.5 of the lead's 1.0) halves it."""
    movies = [
        make_movie(id="lead", ml_rating=3.5, ml_rating_count=1000),
        make_movie(id="cameo", ml_rating=3.5, ml_rating_count=1000),
    ]
    funny = {"lead": 0.8, "cameo": 0.8}
    sig = Signals(tags=funny, person={"lead": 1.0, "cameo": 0.5})
    with_person = combined_rank(movies, SearchCriteria(person="x", tags=[TagCriterion(idx=0)]), sig)
    mood_only = combined_rank(movies, SearchCriteria(tags=[TagCriterion(idx=0)]), Signals(tags=funny))
    by_id = {r.movie.id: r.score for r in with_person.items}
    assert by_id["lead"] == pytest.approx(mood_only.items[0].score)  # the person adds nothing
    assert by_id["cameo"] == pytest.approx(by_id["lead"] / 2)


def test_a_misspelt_person_does_not_lower_the_match(make_movie):
    movies = [make_movie(id="a", ml_rating=3.5, ml_rating_count=1000)]
    exact = combined_rank(movies, SearchCriteria(person="x"), Signals(person={"a": 1.0}))
    typo = combined_rank(movies, SearchCriteria(person="x"), Signals(person={"a": 0.7}))  # found by similarity only
    assert exact.items[0].match_percent == typo.items[0].match_percent


def test_stream_filter_keeps_only_the_named_services(make_movie):
    from cinesense.core.models import Availability, StreamingOption

    def on(service, kind="subscription"):
        return Availability(streaming_de=[StreamingOption(service=service, type=kind)])

    movies = [
        make_movie(id="prime", availability=on("Prime Video")),
        make_movie(id="prime-free", availability=on("Prime Video", "free")),
        make_movie(id="prime-rent", availability=on("Prime Video", "rent")),
        make_movie(id="netflix", availability=on("Netflix")),
        make_movie(id="unknown"),
    ]
    c = SearchCriteria(availability="stream", streaming_services=["Prime Video"])
    res = combined_rank(movies, c, Signals(), offset=0, limit=10)
    assert {r.movie.id for r in res.items} == {"prime", "prime-free", "unknown"}


def test_films_resolved_as_streaming_get_the_streaming_reason(make_movie):
    """The explanation only says a film streams when its reasons do; a lookup during the search must add it."""
    from cinesense.search.service import SearchService

    movies = [make_movie(id="m0", imdb_id="tt0")]
    res = SearchService(FakeProvider(movies), streaming=FakeStreaming({"tt0"})).run(
        SearchCriteria(availability="stream"), 0, 1
    )
    assert "streaming on Netflix" in res.items[0].reasons


def test_named_service_drops_films_streaming_elsewhere(make_movie):
    from cinesense.search.service import SearchService

    movies = [make_movie(id=f"m{i}", imdb_id=f"tt{i}", ml_rating=4.5 - i / 5) for i in range(3)]
    res = SearchService(FakeProvider(movies), streaming=FakeStreaming({"tt0", "tt1"})).run(
        SearchCriteria(availability="stream", streaming_services=["Prime Video"]), 0, 3
    )
    assert res.items == []


class CachedStreaming(FakeStreaming):
    """Everything is in the cache: lookups cost no API call."""

    def cached_de(self, imdb_id):
        return self.get_de(imdb_id)


def test_cached_lookups_do_not_use_up_the_check_limit(make_movie):
    """With a named service most top films stream elsewhere; cached answers are free, so the search looks further."""
    from cinesense.search.service import STREAM_CHECK_LIMIT, SearchService

    n = STREAM_CHECK_LIMIT + 20
    movies = [make_movie(id=f"m{i}", imdb_id=f"tt{i}", ml_rating=4.9 - i / 100) for i in range(n)]
    streaming = CachedStreaming({f"tt{n - 1}"})
    res = SearchService(FakeProvider(movies), streaming=streaming).run(
        SearchCriteria(availability="stream", streaming_services=["Netflix"]), 0, 1
    )
    assert [r.movie.id for r in res.items] == [f"m{n - 1}"]


def test_named_service_puts_confirmed_films_before_unknown_ones(make_movie):
    from cinesense.search.service import SearchService

    movies = [make_movie(id="unknown", imdb_id=None, ml_rating=4.9), make_movie(id="on", imdb_id="tt1", ml_rating=3.0)]
    res = SearchService(FakeProvider(movies), streaming=FakeStreaming({"tt1"})).run(
        SearchCriteria(availability="stream", streaming_services=["Netflix"]), 0, 2
    )
    assert [r.movie.id for r in res.items] == ["on", "unknown"]
