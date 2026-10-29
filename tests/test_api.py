from fastapi.testclient import TestClient

from cinesense.api.app import create_app


def test_health():
    client = TestClient(create_app())
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def client() -> TestClient:
    return TestClient(create_app())


def test_worlds_returns_six():
    r = client().get("/api/worlds")
    assert r.status_code == 200
    assert [w["id"] for w in r.json()] == ["spannung", "scifi", "gefuehl", "abenteuer", "humor", "action"]


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


def test_home_has_24_tiles_from_all_worlds():
    data = client().get("/api/home").json()
    assert len(data["worlds"]) == 6
    assert len(data["tiles"]) == 24
    covered = {wid for t in data["tiles"] for wid in t["world_ids"]}
    assert {"spannung", "scifi", "gefuehl", "abenteuer", "humor", "action"} <= covered
    assert data["titles"] and all(isinstance(t, str) for t in data["titles"])


def test_related_uses_requested_world_for_multi_world_film():
    c = client()
    film = c.get("/api/movies/demo-28").json()
    assert film["world_ids"] == ["abenteuer", "humor"]
    items = c.get("/api/movies/demo-28/related?world_id=humor").json()
    assert items and all("humor" in i["movie"]["world_ids"] for i in items)


def test_cors_allows_local_dev_origins_on_any_port():
    r = client().get("/api/health", headers={"Origin": "http://127.0.0.1:3001"})
    assert r.headers.get("access-control-allow-origin") == "http://127.0.0.1:3001"
