"""Suggestions while typing in the advanced search: catalogue titles and people, typo-tolerant."""

from tests.web_api.test_api import client


def test_title_suggestions_tolerate_typos_and_show_the_year():
    r = client().get("/api/suggest", params={"field": "title", "q": "matrx"})
    assert r.status_code == 200
    assert r.json()[0] == {"value": "The Matrix", "label": "The Matrix (1999)"}


def test_person_suggestions_are_distinct_names():
    r = client().get("/api/suggest", params={"field": "person", "q": "keanu"})
    names = [s["value"] for s in r.json()]
    assert names[0] == "Keanu Reeves"
    assert len(names) == len(set(names))


def test_person_suggestions_respect_the_role():
    r = client().get("/api/suggest", params={"field": "person", "q": "wachowski", "role": "cast"})
    assert r.json() == []
    r = client().get("/api/suggest", params={"field": "person", "q": "wachowski", "role": "director"})
    assert {s["value"] for s in r.json()} >= {"Lana Wachowski", "Lilly Wachowski"}


def test_short_input_and_unknown_field():
    assert client().get("/api/suggest", params={"field": "title", "q": "m"}).json() == []
    assert client().get("/api/suggest", params={"field": "plot", "q": "matrix"}).status_code == 422
