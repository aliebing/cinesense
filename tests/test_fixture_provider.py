from cinesense.providers.fixture import FixtureProvider

WORLD_IDS = ["suspense", "scifi", "romance", "adventure", "comedy", "action"]


def test_loads_real_fixture_with_tags():
    p = FixtureProvider()
    movies = p.list_movies()
    assert 40 <= len(movies) <= 60
    assert not any(m.is_placeholder for m in movies)
    assert len(p.list_tags()) == 1128


def test_every_world_has_films():
    movies = FixtureProvider().list_movies()
    for wid in WORLD_IDS:
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
