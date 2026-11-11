from cinesense.data_sources.fixture import FixtureProvider

WORLD_IDS = ["suspense", "scifi", "romance", "adventure", "comedy", "action", "drama"]


def test_loads_real_fixture_with_tags():
    p = FixtureProvider()
    movies = p.list_movies()
    assert 40 <= len(movies) <= 60
    assert not any(m.is_placeholder for m in movies)
    assert len(p.list_tags()) == 1128


def test_every_world_has_films():
    movies = FixtureProvider().list_movies()
    for wid in WORLD_IDS:
        if wid == "drama":
            continue  # the fixture's 54 well-known films hold no pure drama or war film (Drama & Life's fallback)
        assert sum(wid in m.world_ids for m in movies) >= 8


def test_get_movie_and_unknown():
    p = FixtureProvider()
    assert p.get_movie("ml-2571").title == "The Matrix"
    assert p.get_movie("nope") is None


def test_fixture_contains_edge_cases():
    movies = FixtureProvider().list_movies()
    assert any(m.youtube_key is None for m in movies)
    assert any(m.availability.streaming_de is None for m in movies)
    assert any(m.availability.streaming_de is not None for m in movies)


def test_title_search_also_matches_the_german_title():
    from cinesense.core.models import Movie
    from cinesense.data_sources.fixture import FixtureProvider

    p = FixtureProvider()
    p.upsert_live([Movie(id="imdb-tt0057687", title="Apache Gold", title_de="Winnetou 1. Teil", year=1963)])
    assert p.search_title("Winnetou").get("imdb-tt0057687", 0) >= 0.85
