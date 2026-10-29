import numpy as np

from cinesense.domain.criteria import SearchCriteria
from cinesense.personal.feedback import MemoryFeedbackStore
from cinesense.personal.profile import Profile, build_profile
from cinesense.providers.fixture import FixtureProvider
from cinesense.search.service import SearchService


def film_id(p, title):
    return next(m.id for m in p.list_movies() if m.title == title)


def test_memory_store_set_toggle_clear():
    s = MemoryFeedbackStore()
    s.set("u1", "a", 1)
    s.set("u1", "b", -1)
    s.set("u1", "a", 0)  # toggled off
    assert s.get("u1") == {"b": -1} and s.get("u2") == {}
    s.clear("u1")
    assert s.get("u1") == {}


def test_profile_from_likes_picks_their_strong_tags():
    p = FixtureProvider()
    matrix = film_id(p, "The Matrix")
    prof = build_profile({matrix: 1}, p)
    vec = p.tag_vectors([matrix])[0]
    assert prof.liked == [matrix] and 1 <= len(prof.taste) <= 8
    assert all(vec[i] >= 0.5 for i in prof.taste) and max(prof.taste.values()) == 10
    assert prof.taste_names[0] == p.list_tags()[max(prof.taste, key=prof.taste.get)]


def test_profile_without_vectors_is_safe():
    p = FixtureProvider()
    prof = build_profile({"wd-Q1": 1, "imdb-tt0": -1}, p)
    assert prof.taste == {} and prof.liked == ["wd-Q1"] and prof.disliked == ["imdb-tt0"]


def test_disliked_film_hidden_and_counted():
    p = FixtureProvider()
    titanic = film_id(p, "Titanic")
    prof = build_profile({titanic: -1}, p)
    base = SearchService(p).run(SearchCriteria(), 0, 100)
    out = SearchService(p).run(SearchCriteria(), 0, 100, profile=prof)
    assert titanic not in [r.movie.id for r in out.items]
    assert out.total == base.total - 1 and out.hidden_by_exclusion == base.hidden_by_exclusion + 1


def test_profile_boosts_matching_film_with_reason():
    p = FixtureProvider()
    matrix = film_id(p, "The Matrix")
    prof = build_profile({matrix: 1}, p)
    base = [r.movie.id for r in SearchService(p).run(SearchCriteria(), 0, 100).items]
    ranked = SearchService(p).run(SearchCriteria(), 0, 100, profile=prof).items
    fits = [r.movie.id for r in ranked if "fits your taste" in r.reasons and r.movie.id != matrix]
    assert fits, "some other film must match the taste"
    personal = [r.movie.id for r in ranked]
    assert personal.index(fits[0]) < base.index(fits[0])
    assert Profile.empty().taste == {}


def test_mean_tag_vector_shape():
    v = FixtureProvider().mean_tag_vector()
    assert v.shape == (1128,) and np.isfinite(v).all()


def test_profile_hits_and_profile_are_cached_per_feedback_state():
    from cinesense.api.personal import cached_profile

    class Counting(FixtureProvider):
        calls = {"tag_search": 0, "tag_vectors": 0}

        def tag_search(self, *a, **k):
            self.calls["tag_search"] += 1
            return super().tag_search(*a, **k)

        def tag_vectors(self, ids):
            self.calls["tag_vectors"] += 1
            return super().tag_vectors(ids)

    p = Counting()
    matrix = film_id(p, "The Matrix")
    prof = cached_profile({matrix: 1}, p)
    assert cached_profile({matrix: 1}, p) is prof and p.calls["tag_vectors"] == 1
    SearchService(p).run(SearchCriteria(), 0, 10, profile=prof)
    SearchService(p).run(SearchCriteria(), 0, 10, profile=prof)
    assert p.calls["tag_search"] == 1
    assert cached_profile({matrix: 1, film_id(p, "Titanic"): -1}, p) is not prof
