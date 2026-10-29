from fastapi.testclient import TestClient

from cinesense.api.app import create_app
from cinesense.api.deps import get_embedder, get_provider, get_streaming
from cinesense.providers.fixture import FixtureProvider


def make_app(provider=None, streaming=None):
    app = create_app(load_env=False)
    app.dependency_overrides[get_provider] = lambda: provider or FixtureProvider()
    app.dependency_overrides[get_streaming] = lambda: streaming
    app.dependency_overrides[get_embedder] = lambda: None
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
    assert c.get("/api/movies/demo-01").json()["title"] == "Demo-Film 01"
    r = c.get("/api/movies/nope")
    assert r.status_code == 404
    assert r.json()["detail"] == "movie_not_found"


def test_related_excludes_self():
    c = client()
    items = c.get("/api/movies/demo-01/related").json()
    assert items and all(i["movie"]["id"] != "demo-01" for i in items)
    assert len(items) <= 13
    assert c.get("/api/movies/nope/related").status_code == 404


def test_home_rows_per_world():
    data = client().get("/api/home").json()
    assert len(data["worlds"]) == 6
    assert set(data["rows"]) == {"suspense", "scifi", "romance", "adventure", "comedy", "action"}
    for wid, films in data["rows"].items():
        assert 0 < len(films) <= 12 and all(wid in f["world_ids"] for f in films)
    assert len(data["tiles"]) == 24
    covered = {wid for t in data["tiles"] for wid in t["world_ids"]}
    assert {"suspense", "scifi", "romance", "adventure", "comedy", "action"} <= covered
    assert data["titles"] and all(isinstance(t, str) for t in data["titles"])


def test_related_uses_requested_world_for_multi_world_film():
    c = client()
    film = c.get("/api/movies/demo-28").json()
    assert film["world_ids"] == ["adventure", "comedy"]
    items = c.get("/api/movies/demo-28/related?world_id=comedy").json()
    assert items and all("comedy" in i["movie"]["world_ids"] for i in items)


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
    data = (
        client().post("/api/discover", json={"criteria": {"exclude_genres": ["Horror"]}, "limit": 50}).json()
    )
    assert all("Horror" not in i["movie"]["genres"] for i in data["items"])
    assert data["hidden_by_exclusion"] >= 1


def test_movie_detail_adds_streaming():
    from cinesense.domain.models import StreamingOption

    stub = StubStreaming([StreamingOption(service="Netflix", type="subscription")])
    body = client(streaming=stub).get("/api/movies/demo-01").json()
    assert body["availability"]["subscription_services"] == ["Netflix"]


def test_movie_detail_streaming_unknown_when_none():
    body = client(streaming=StubStreaming(None)).get("/api/movies/demo-01").json()
    assert body["availability"]["streaming_de"] is None


def test_home_fills_title_art_from_streaming_images():
    from cinesense.providers.streaming import ImageSet

    class ImgStub(StubStreaming):
        calls = 0

        def images(self, imdb_id):
            ImgStub.calls += 1
            return ImageSet("v.jpg", "h.jpg", "b.jpg")

    data = client(streaming=ImgStub(None)).get("/api/home").json()
    first = next(iter(data["rows"].values()))[0]
    assert first["horizontal_poster_url"] in ("h.jpg", first["horizontal_poster_url"])
    assert ImgStub.calls <= 72
