"""Autocorrect for the advanced search: a misspelt person or title is answered with the name that was found."""

from cinesense.core.criteria import SearchCriteria
from cinesense.search.service import SearchService, correction


class Provider:
    def __init__(self, movies, title_hits=None, person_hits=None):
        self.movies = movies
        self.title_hits = title_hits or {}
        self.person_hits = person_hits or ({}, {})

    def list_tags(self):
        return []

    def list_movies(self):
        return list(self.movies)

    def search_title(self, q, limit=200):
        return self.title_hits

    def search_person(self, q, role="any", limit=400):
        return self.person_hits


def test_correction_only_when_the_input_is_not_part_of_the_match():
    assert correction("sandra bullok", "Sandra Bullock") == "Sandra Bullock"
    assert correction("bullock", "Sandra Bullock") is None  # already right, just shorter
    assert correction("sandra hüller", "Sandra Hüller") is None  # same name, only case and accents
    assert correction("lord of the rings", "The Lord of the Rings: The Two Towers") is None
    assert correction("x", None) is None


def test_correction_drops_the_movielens_alternative_title():
    assert correction("amelei", "Amelie (Fabuleux destin d'Amélie Poulain, Le)") == "Amelie"


def test_a_misspelt_person_is_corrected_to_the_best_match(make_movie):
    movies = [make_movie(id="a", title="Speed"), make_movie(id="b", title="Gravity")]
    p = Provider(movies, person_hits=({"a": 0.9, "b": 0.6}, {"a": "Sandra Bullock", "b": "Sandra Bullock"}))
    page = SearchService(p).run(SearchCriteria(person="sandra bullok"))
    assert page.corrected_person == "Sandra Bullock"
    assert page.corrected_title is None


def test_a_misspelt_title_is_corrected_to_the_best_match(make_movie):
    movies = [make_movie(id="a", title="Inception"), make_movie(id="b", title="Interception")]
    page = SearchService(Provider(movies, title_hits={"a": 0.8, "b": 0.6})).run(SearchCriteria(title="inceptoin"))
    assert page.corrected_title == "Inception"


def test_nothing_found_means_nothing_to_correct(make_movie):
    page = SearchService(Provider([make_movie(id="a")])).run(SearchCriteria(person="qwertz"))
    assert page.corrected_person is None
