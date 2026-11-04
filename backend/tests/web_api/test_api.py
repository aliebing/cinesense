from fastapi.testclient import TestClient

from cinesense.data_sources.fixture import FixtureProvider
from cinesense.web_api.app import create_app
from cinesense.web_api.deps import (
    get_embedder,
    get_live,
    get_provider,
    get_streaming,
    get_trailer_checker,
    get_trailers,
)


def make_app(provider=None, streaming=None, trailers=None):
    app = create_app(load_env=False)
    app.dependency_overrides[get_provider] = lambda: provider or FixtureProvider()
    app.dependency_overrides[get_streaming] = lambda: streaming
    app.dependency_overrides[get_embedder] = lambda: None
    app.dependency_overrides[get_live] = lambda: None
    app.dependency_overrides[get_trailers] = lambda: trailers
    app.dependency_overrides[get_trailer_checker] = lambda: None
    return app


def test_health():
    client = TestClient(make_app())
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def client(**kw) -> TestClient:
    return TestClient(make_app(**kw))


def test_worlds_returns_six():
    r = client().get("/api/worlds")
    assert r.status_code == 200
    assert [w["id"] for w in r.json()] == ["suspense", "scifi", "romance", "adventure", "comedy", "action"]


def test_world_movies_ranked_and_limited():
    r = client().get("/api/worlds/action/movies?limit=5")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 5
    assert all("action" in i["movie"]["world_ids"] for i in items)
    percents = [i["match_percent"] for i in items]
    assert percents == sorted(percents, reverse=True)


def test_unknown_world_404():
    r = client().get("/api/worlds/horror/movies")
    assert r.status_code == 404
    assert r.json()["detail"] == "world_not_found"


def test_movie_detail_and_404():
    c = client()
    assert c.get("/api/movies/ml-2571").json()["title"] == "The Matrix"
    r = c.get("/api/movies/nope")
    assert r.status_code == 404
    assert r.json()["detail"] == "movie_not_found"


def test_related_excludes_self():
    c = client()
    items = c.get("/api/movies/ml-2571/related").json()
    assert items and all(i["movie"]["id"] != "ml-2571" for i in items)
    assert len(items) <= 13
    assert c.get("/api/movies/nope/related").status_code == 404


def test_home_rows_per_world():
    data = client().get("/api/home").json()
    assert len(data["worlds"]) == 6
    assert set(data["rows"]) == {"suspense", "scifi", "romance", "adventure", "comedy", "action"}
    for wid, films in data["rows"].items():
        assert 0 < len(films) <= 16 and all(wid in f["world_ids"] for f in films)
    assert len(data["tiles"]) == 24
    covered = {wid for t in data["tiles"] for wid in t["world_ids"]}
    assert {"suspense", "scifi", "romance", "adventure", "comedy", "action"} <= covered
    assert data["titles"] and all(isinstance(t, str) for t in data["titles"])


def test_related_uses_requested_world_for_multi_world_film():
    c = client()
    film = c.get("/api/movies/ml-2571").json()
    assert film["world_ids"][0] == "suspense" and "scifi" in film["world_ids"]
    items = c.get("/api/movies/ml-2571/related?world_id=scifi").json()
    assert items and all("scifi" in i["movie"]["world_ids"] for i in items)


def test_cors_allows_local_dev_origins_on_any_port():
    r = client().get("/api/health", headers={"Origin": "http://127.0.0.1:3001"})
    assert r.headers.get("access-control-allow-origin") == "http://127.0.0.1:3001"


class StubStreaming:
    def __init__(self, options):
        self.options = options

    def get_de(self, imdb_id):
        return self.options

    def images(self, imdb_id):
        return None


def test_tags_endpoint_lists_fixture_tags():
    r = client().get("/api/tags")
    assert r.status_code == 200 and isinstance(r.json(), list)


def test_discover_validates_weights():
    r = client().post("/api/discover", json={"criteria": {"tags": [{"idx": 1, "weight": 0}]}})
    assert r.status_code == 422


def test_discover_paging_and_total():
    c = client()
    first = c.post("/api/discover", json={"criteria": {}, "offset": 0, "limit": 5}).json()
    second = c.post("/api/discover", json={"criteria": {}, "offset": 5, "limit": 5}).json()
    assert first["total"] == second["total"] >= 10
    assert {i["movie"]["id"] for i in first["items"]}.isdisjoint({i["movie"]["id"] for i in second["items"]})


def test_discover_no_horror_hides_and_counts():
    data = client().post("/api/discover", json={"criteria": {"exclude_genres": ["Horror"]}, "limit": 50}).json()
    assert all("Horror" not in i["movie"]["genres"] for i in data["items"])
    assert data["hidden_by_exclusion"] >= 1


def test_movie_detail_adds_streaming():
    from cinesense.core.models import StreamingOption

    stub = StubStreaming([StreamingOption(service="Netflix", type="subscription")])
    body = client(streaming=stub).get("/api/movies/ml-2571").json()
    assert body["availability"]["subscription_services"] == ["Netflix"]


def test_movie_detail_streaming_unknown_when_none():
    body = client(streaming=StubStreaming(None)).get("/api/movies/ml-2571").json()
    assert body["availability"]["streaming_de"] is None


def test_home_fills_title_art_from_streaming_images():
    from cinesense.data_sources.streaming import ImageSet

    class ImgStub(StubStreaming):
        calls = 0

        def images(self, imdb_id):
            ImgStub.calls += 1
            return ImageSet("v.jpg", "h.jpg", "b.jpg")

    data = client(streaming=ImgStub(None)).get("/api/home").json()
    first = next(iter(data["rows"].values()))[0]
    assert first["horizontal_poster_url"] in ("h.jpg", first["horizontal_poster_url"])
    assert ImgStub.calls <= 72


def test_wikidata_key_skips_youtube_api():
    class Spy:
        calls = 0

        def find_trailer(self, film_id, title, year):
            Spy.calls += 1
            return "yt-fallback"

    c = client(trailers=Spy())
    assert c.get("/api/movies/ml-2571").json()["youtube_key"] not in (None, "yt-fallback")  # Wikidata key
    no_key = next(m for m in FixtureProvider().list_movies() if m.youtube_key is None)
    assert c.get(f"/api/movies/{no_key.id}").json()["youtube_key"] == "yt-fallback"
    assert Spy.calls == 1


def test_images_checked_films_skip_streaming_lookups():
    class CountingStreaming(StubStreaming):
        def __init__(self):
            super().__init__(None)
            self.image_calls = 0

        def images(self, imdb_id):
            from cinesense.data_sources.streaming import ImageSet

            self.image_calls += 1
            return ImageSet(None, None, None)  # looked up, nothing found -> mark checked, never ask again

    s = CountingStreaming()
    prov = FixtureProvider()
    c = client(provider=prov, streaming=s)
    c.get("/api/home")
    first = s.image_calls
    c.get("/api/home")
    assert first > 0 and s.image_calls == first


def test_home_rows_never_repeat_a_film():
    data = client().get("/api/home").json()
    ids = [f["id"] for films in data["rows"].values() for f in films]
    assert len(ids) == len(set(ids))


def test_trailer_report_endpoint_validates_ids():
    c = client()
    assert c.post("/api/trailers/report", json={"video_id": "abc_DEF-123"}).status_code in (204, 400)
    assert c.post("/api/trailers/report", json={"video_id": "<script>"}).status_code == 422


def test_trailer_report_requires_a_user_and_a_known_trailer():
    from cinesense.data_sources.trailer_check import TrailerChecker
    from cinesense.data_sources.youtube import MemoryTrailerStore
    from cinesense.web_api.deps import get_trailer_checker

    app = make_app()
    checker = TrailerChecker(MemoryTrailerStore())
    app.dependency_overrides[get_trailer_checker] = lambda: checker
    c = TestClient(app)
    key = next(m.youtube_key for m in FixtureProvider().list_movies() if m.youtube_key)
    user = {"X-CineSense-User": "0b6f7c1e-2c55-4c4e-9a0b-4d1f3f1a2b3c"}
    assert c.post("/api/trailers/report", json={"video_id": key}).status_code == 400  # no user
    assert c.post("/api/trailers/report", json={"video_id": "unknownXYZ1"}, headers=user).status_code == 404
    assert c.post("/api/trailers/report", json={"video_id": key}, headers=user).status_code == 204
    assert checker.playable(key) is False


def test_stage_never_offers_a_reported_fallback_trailer():
    from cinesense.data_sources.trailer_check import TrailerChecker
    from cinesense.data_sources.youtube import MemoryTrailerStore
    from cinesense.web_api.deps import get_trailer_checker

    class Fallback:
        def find_trailer(self, film_id, title, year):
            return "fallbackBad1"

    checker = TrailerChecker(MemoryTrailerStore())
    checker.mark_bad("fallbackBad1")
    film = next(m for m in FixtureProvider().list_movies() if not m.youtube_key)
    app = make_app(trailers=Fallback())
    app.dependency_overrides[get_trailer_checker] = lambda: checker
    assert TestClient(app).get(f"/api/movies/{film.id}").json()["youtube_key"] is None


def test_discover_can_skip_image_lookups():
    """Homepage background rows ask with fill_images=false, so they never spend Streaming API budget."""

    class CountingStreaming(StubStreaming):
        def __init__(self):
            super().__init__(None)
            self.image_calls = 0

        def images(self, imdb_id):
            self.image_calls += 1
            return None

    s = CountingStreaming()
    c = client(streaming=s)
    body = {"criteria": {"world_id": "scifi"}, "limit": 12}
    assert c.post("/api/discover", json={**body, "fill_images": False}).status_code == 200
    assert s.image_calls == 0
    c.post("/api/discover", json=body)
    assert s.image_calls > 0


def test_search_fills_youtube_trailers_for_the_top_hits_only():
    """The search rows play trailers on hover: the top hits without a Wikidata trailer ask YouTube, the rest don't."""
    from cinesense.web_api.app import TRAILER_FILL

    asked = []

    class Fallback:
        def find_trailer(self, film_id, title, year):
            asked.append(film_id)
            return f"yt-{film_id}"

    prov = FixtureProvider()
    for m in prov._movies[::2]:  # half the catalogue without a Wikidata trailer
        m.youtube_key = None
    before = client(provider=prov).post("/api/search", json={"limit": 20}).json()["items"]
    expected = [r["movie"]["id"] for r in before[:TRAILER_FILL] if r["movie"]["youtube_key"] is None]
    after = client(provider=prov, trailers=Fallback()).post("/api/search", json={"limit": 20}).json()["items"]
    assert expected and asked == expected
    assert [r["movie"]["youtube_key"] for r in after[:TRAILER_FILL] if r["movie"]["id"] in expected] == [
        f"yt-{i}" for i in expected
    ]


def test_discover_hits_get_trailers_but_background_rows_spend_nothing():
    asked = []

    class Fallback:
        def find_trailer(self, film_id, title, year):
            asked.append(film_id)
            return "yt-fallback"

    prov = FixtureProvider()
    for m in prov._movies:
        m.youtube_key = None
    c = client(provider=prov, trailers=Fallback())
    c.post("/api/discover", json={"limit": 20, "fill_images": False})
    assert asked == []
    c.post("/api/discover", json={"limit": 20})
    assert asked


def test_search_offers_relaxations_when_thin():
    r = client().post("/api/search", json={"criteria": {"max_runtime_min": 60}}).json()
    assert r["total"] < 3
    assert [o["id"] for o in r["relaxations"]] == ["runtime"]
    assert r["relaxations"][0]["label"] == "Allow up to 90 min"
    assert r["relaxations"][0]["count"] > r["total"]
    assert r["relaxations"][0]["criteria"]["max_runtime_min"] == 90


def test_search_without_relaxations_when_enough():
    assert client().post("/api/search", json={"criteria": {}}).json()["relaxations"] == []


def test_search_offers_no_relaxations_on_later_pages():
    r = client().post("/api/search", json={"criteria": {"max_runtime_min": 60}, "offset": 20}).json()
    assert r["relaxations"] == []


def test_search_marks_misses_against_relaxed_from():
    body = {"criteria": {"max_runtime_min": 90}, "relaxed_from": {"max_runtime_min": 60}}
    items = {i["movie"]["title"]: i["misses"] for i in client().post("/api/search", json=body).json()["items"]}
    assert items == {"Shrek": ["90 min, longer than 60"], "Toy Story": ["80 min, longer than 60"]}


def test_search_without_relaxed_from_has_no_misses():
    items = client().post("/api/search", json={"criteria": {"max_runtime_min": 90}}).json()["items"]
    assert items and all(i["misses"] == [] for i in items)


def test_misses_name_moods_the_film_has_no_data_for():
    p = FixtureProvider()
    p._vectors.pop("ml-4306")  # Shrek without Tag Genome data
    funny = p.list_tags().index("funny")
    body = {"criteria": {"max_runtime_min": 90}, "relaxed_from": {"tags": [{"idx": funny}], "max_runtime_min": 90}}
    res = client(provider=p).post("/api/search", json=body).json()["items"]
    items = {i["movie"]["title"]: i["misses"] for i in res}
    assert items["Shrek"] == ["no mood data for 'funny'"] and items["Toy Story"] == []


def test_search_reports_what_each_exclusion_hides():
    r = client().post("/api/search", json={"criteria": {"person": "Keanu Reeves", "exclude_genres": ["Horror"]}})
    assert r.json()["hidden_by"] == {"genre:Horror": 0}
