from cinesense.providers.fixture import FixtureProvider

WORLD_IDS = ["suspense", "scifi", "romance", "adventure", "comedy", "action"]


def test_loads_48_placeholder_movies():
    movies = FixtureProvider().list_movies()
    assert len(movies) == 48
    assert all(m.is_placeholder and m.title.startswith("Demo-Film") for m in movies)
    assert all(m.overview.startswith("Placeholder") for m in movies)


def test_every_world_has_eight_movies():
    movies = FixtureProvider().list_movies()
    for wid in WORLD_IDS:
        assert sum(wid in m.world_ids for m in movies) >= 8


def test_get_movie_and_unknown():
    p = FixtureProvider()
    assert p.get_movie("demo-01").title == "Demo-Film 01"
    assert p.get_movie("nope") is None


def test_fixture_contains_edge_cases():
    movies = FixtureProvider().list_movies()
    assert any(m.youtube_key is None for m in movies)
    assert any(m.poster_url is None for m in movies)
    assert any("Horror" in m.genres for m in movies)
    assert any(not m.availability.in_cinema_de and not m.availability.streaming_flatrate_de for m in movies)
