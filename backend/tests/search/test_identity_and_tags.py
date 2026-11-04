"""Person and title pick the films; mood tags only rank them (prefer) or narrow them (must / not), and every
filter holds together (AND), for catalogue films and for films the live search adds."""

import numpy as np

from cinesense.core.criteria import SearchCriteria, TagCriterion
from cinesense.search.service import SearchService

ACTION, FUNNY, DARK = 0, 1, 2


class Provider:
    """Speed and Speed 2 star Sandra Bullock; the tag search's top list holds neither (as in the real catalogue)."""

    def __init__(self, movies, vectors):
        self.movies, self.vectors = movies, vectors
        self.inserted = []

    def list_tags(self):
        return ["action", "funny", "dark"]

    def list_movies(self):
        return list(self.movies)

    def tag_search(self, weights, must, exclude, must_threshold, not_threshold, limit=500):
        return [("popcorn", 0.9)], 0  # top films by tags: none of the Speed films

    def tag_vectors(self, ids):
        return np.array([self.vectors.get(i, [np.nan] * 3) for i in ids], dtype=float)

    def search_title(self, q, limit=200):
        return {m.id: 0.9 for m in self.movies if q.lower() in m.title.lower()}

    def search_person(self, q, role="any", limit=400):
        ids = {"speed": 1.0, "speed2": 1.0, "net": 1.0}
        return ({i: s for i, s in ids.items()}, {i: "Sandra Bullock" for i in ids})

    def upsert_live(self, movies):
        self.inserted += movies


def catalogue(make_movie):
    movies = [
        make_movie(id="speed", title="Speed", genres=["Action"]),
        make_movie(id="speed2", title="Speed 2: Cruise Control", genres=["Action"]),
        make_movie(id="net", title="The Net", genres=["Thriller"]),
        make_movie(id="popcorn", title="Popcorn Speed Run", genres=["Comedy"]),
    ]
    vectors = {"speed": [0.9, 0.3, 0.2], "speed2": [0.8, 0.2, 0.7], "net": [0.4, 0.1, 0.6], "popcorn": [0.9, 0.9, 0.1]}
    return Provider(movies, vectors)


def ids(page):
    return [r.movie.id for r in page.items]


def test_prefer_tags_rank_the_person_and_title_hits_instead_of_picking_others(make_movie):
    c = SearchCriteria(
        person="Sandra Bullock",
        title="Speed",
        tags=[TagCriterion(idx=ACTION, weight=6, mode="prefer"), TagCriterion(idx=FUNNY, weight=8, mode="prefer")],
    )
    assert sorted(ids(SearchService(catalogue(make_movie)).run(c))) == ["speed", "speed2"]


def test_not_tags_still_hide_person_and_title_hits(make_movie):
    c = SearchCriteria(
        person="Sandra Bullock",
        title="Speed",
        tags=[TagCriterion(idx=ACTION, weight=6, mode="prefer"), TagCriterion(idx=DARK, weight=6, mode="not")],
    )
    page = SearchService(catalogue(make_movie)).run(c)
    assert ids(page) == ["speed"]  # Speed 2 is too dark
    assert page.hidden_by_exclusion == 1


def test_must_tags_narrow_the_person_hits(make_movie):
    c = SearchCriteria(person="Sandra Bullock", tags=[TagCriterion(idx=DARK, weight=6, mode="must")])
    assert sorted(ids(SearchService(catalogue(make_movie)).run(c))) == ["net", "speed2"]


class Live:
    def __init__(self, movie_cls):
        self.movie_cls = movie_cls

    def search_title(self, q):
        return [
            self.movie_cls(id="wd-metal", title="Metal Skin Speed"),
            self.movie_cls(id="wd-speed3", title="Speed 3"),
        ]

    def search_person(self, q):
        return "Sandra Bullock", [
            self.movie_cls(id="wd-speed3", title="Speed 3"),
            self.movie_cls(id="wd-gravity", title="Gravity"),
        ]


def test_live_hits_must_match_person_and_title_together(make_movie):
    from cinesense.core.models import Movie

    p = catalogue(make_movie)
    c = SearchCriteria(person="Sandra Bullock", title="Speed", extended=True)
    found = ids(SearchService(p, live=Live(Movie)).run(c))
    assert "wd-speed3" in found  # in both live searches
    assert "wd-metal" not in found  # title only
    assert "wd-gravity" not in found  # person only


def test_each_exclusion_says_how_many_films_it_hides_here(make_movie):
    c = SearchCriteria(
        person="Sandra Bullock",
        title="Speed",
        exclude_genres=["Horror"],
        tags=[TagCriterion(idx=DARK, weight=6, mode="not")],
    )
    page = SearchService(catalogue(make_movie)).run(c)
    assert page.hidden_by == {"tag:2": 1, "genre:Horror": 0}  # Speed 2 is too dark; no horror among the hits
