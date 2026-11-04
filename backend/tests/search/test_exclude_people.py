"""Excluded people ("action like Stallone films, but without Stallone"): their films drop out of every search,
a misspelt name included; the chip says how many films each one hid."""

import pytest
from pydantic import ValidationError

from cinesense.core.criteria import SearchCriteria
from cinesense.search.service import SearchService


class Provider:
    def __init__(self, movies, people):
        self.movies = movies
        self.people = people  # query -> (film id -> score, film id -> name)

    def list_tags(self):
        return []

    def list_movies(self):
        return list(self.movies)

    def search_person(self, q, role="any", limit=400):
        return self.people.get(q, ({}, {}))


@pytest.fixture
def films(make_movie):
    return [
        make_movie(id="rambo", title="Rambo", genres=["Action"]),
        make_movie(id="t2", title="Terminator 2", genres=["Action"]),
        make_movie(id="diehard", title="Die Hard", genres=["Action"]),
        make_movie(id="expendables", title="The Expendables", genres=["Action"]),
    ]


PEOPLE = {
    "stalone": (
        {"rambo": 1.0, "expendables": 0.8},
        {"rambo": "Sylvester Stallone", "expendables": "Sylvester Stallone"},
    ),
    "Arnold Schwarzenegger": (
        {"t2": 1.0, "expendables": 0.5},
        {"t2": "Arnold Schwarzenegger", "expendables": "Arnold Schwarzenegger"},
    ),
}


def test_films_with_an_excluded_person_drop_out_and_each_chip_counts_what_it_hid(films):
    c = SearchCriteria(exclude_people=["stalone", "Arnold Schwarzenegger"])  # misspelt: the person search corrects
    page = SearchService(Provider(films, PEOPLE)).run(c, limit=10)
    assert [r.movie.id for r in page.items] == ["diehard"]
    assert page.hidden_by["person:stalone"] == 2
    assert page.hidden_by["person:Arnold Schwarzenegger"] == 1  # The Expendables already counted for Stallone
    assert page.hidden_by_exclusion == 3


def test_an_excluded_person_nobody_knows_hides_nothing(films):
    page = SearchService(Provider(films, PEOPLE)).run(SearchCriteria(exclude_people=["Nobody Known"]), limit=10)
    assert len(page.items) == 4
    assert page.hidden_by["person:Nobody Known"] == 0


def test_at_most_five_excluded_people():
    with pytest.raises(ValidationError):
        SearchCriteria(exclude_people=[f"p{i}" for i in range(6)])
