import pytest
from fastapi.testclient import TestClient

from cinesense.web_api.admin_session import LoginThrottle, Sessions

S3CRET_HASH = "$2b$04$Si0ybM4ydQhrtkGwRjbL3uPiSpgKscLp4d1dUZRmqtSMIsVwHaLPq"  # bcrypt (cost 4) of "s3cret"


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("CINESENSE_EVAL_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_USER", "admin")
    monkeypatch.setenv("TECH_PASSWORD_HASH", S3CRET_HASH)
    from cinesense.web_api.app import create_app

    return TestClient(create_app())


def test_sign_in_sets_a_session_cookie_that_opens_the_admin_api(client):
    assert client.get("/api/admin/me").status_code == 401
    assert client.get("/api/admin/visitors").status_code == 401
    r = client.post("/api/admin/login", json={"name": "admin", "password": "s3cret"})
    assert r.status_code == 200
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    assert client.get("/api/admin/me").json() == {"name": "admin"}
    assert client.get("/api/eval/runs").status_code == 200


def test_wrong_password_is_refused(client):
    r = client.post("/api/admin/login", json={"name": "admin", "password": "nope"})
    assert r.status_code == 401 and "set-cookie" not in r.headers
    assert client.get("/api/admin/me").status_code == 401


def test_sign_out_ends_the_session_even_for_a_copied_cookie(client):
    client.post("/api/admin/login", json={"name": "admin", "password": "s3cret"})
    copied = dict(client.cookies)
    assert client.post("/api/admin/logout").status_code == 200
    assert client.get("/api/admin/me").status_code == 401
    client.cookies.update(copied)  # the cookie copied before sign-out
    assert client.get("/api/admin/me").status_code == 401


def test_too_many_failed_sign_ins_are_throttled(client):
    for _ in range(5):
        client.post("/api/admin/login", json={"name": "admin", "password": "nope"})
    r = client.post("/api/admin/login", json={"name": "admin", "password": "s3cret"})
    assert r.status_code == 429 and int(r.headers["retry-after"]) > 0


def test_sessions_are_signed_and_expire():
    s = Sessions()
    token = s.issue("k", now=1000)
    assert s.valid(token, "k", now=1001)
    assert not s.valid(token, "other", now=1001)
    assert not s.valid(token.replace(token[-1], "0" if token[-1] != "0" else "1"), "k", now=1001)
    assert not s.valid(token, "k", now=1000 + 9 * 3600)


def test_throttle_frees_the_ip_after_success():
    t = LoginThrottle(max_failures=2, window_s=60, clock=lambda: 0.0)
    assert t.try_acquire("ip") == 0 and t.try_acquire("ip") == 0
    assert t.try_acquire("ip") > 0
    t.succeeded("ip")
    assert t.try_acquire("ip") == 0


def test_a_user_without_a_valid_hash_keeps_the_admin_closed(monkeypatch, tmp_path):
    """An old plain TECH_PASSWORD or a broken hash must never leave the admin open."""
    monkeypatch.setenv("CINESENSE_EVAL_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_USER", "admin")
    monkeypatch.delenv("TECH_PASSWORD_HASH", raising=False)
    monkeypatch.setenv("TECH_PASSWORD", "s3cret")
    from cinesense.web_api.app import create_app

    client = TestClient(create_app())
    assert client.get("/api/admin/visitors").status_code == 401
    assert client.post("/api/admin/login", json={"name": "admin", "password": "s3cret"}).status_code == 401
    monkeypatch.setenv("TECH_PASSWORD_HASH", "not-a-bcrypt-hash")
    assert client.post("/api/admin/login", json={"name": "admin", "password": "s3cret"}).status_code == 401
