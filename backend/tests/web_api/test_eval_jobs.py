"""The evaluation run started from /admin/evaluation: one at a time, progress for the live view, stop."""

import threading

import pytest
from fastapi.testclient import TestClient

from cinesense.web_api.app import create_app
from cinesense.web_api.eval_jobs import Busy, EvalJob
from cinesense.web_api.eval_view import get_eval_job

S3CRET_HASH = "$2b$04$Si0ybM4ydQhrtkGwRjbL3uPiSpgKscLp4d1dUZRmqtSMIsVwHaLPq"  # bcrypt (cost 4) of "s3cret"


def result(id_, passed):
    return {
        "id": id_,
        "category": "mood",
        "turns": ["x"],
        "passed": passed,
        "cost_usd": 0.01,
        "checks": {"tools": {"ok": passed, "why": [], "applies": True}},
        "results": ["A", "B"],
    }


def fake_work(model, ids, on_progress, should_stop):
    for i in ids:
        on_progress({"event": "scenario", "id": i, "turns": ["x"]})
        on_progress({"event": "result", "result": result(i, i != "b")})
    on_progress({"event": "comparing"})
    return "2026-11-05_1700"


def test_a_run_reports_each_result_and_the_saved_run():
    job = EvalJob(fake_work)
    s = job.start("anthropic/claude-haiku-5.5", ["a", "b"], background=False)
    assert s["status"] == "done" and s["run"] == "2026-11-05_1700"
    assert s["done"] == 2 and s["passed"] == 1 and s["cost_usd"] == 0.02
    assert s["results"][1]["failed_checks"] == ["tools"]


def test_only_one_run_at_a_time_and_stop_ends_it():
    gate = threading.Event()

    def slow(model, ids, on_progress, should_stop):
        gate.wait(5)
        assert should_stop()
        return "2026-11-05_1701"

    job = EvalJob(slow)
    job.start("m", ["a"])
    with pytest.raises(Busy):
        job.start("m", ["a"])
    assert job.stop()["status"] == "stopping"
    gate.set()
    for _ in range(100):
        if job.snapshot()["status"] == "stopped":
            break
        threading.Event().wait(0.02)
    assert job.snapshot()["status"] == "stopped"


def test_a_failing_run_is_reported():
    def broken(*_):
        raise RuntimeError("no database")

    s = EvalJob(broken).start("m", ["a"], background=False)
    assert s["status"] == "failed" and "no database" in s["error"]


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("CINESENSE_EVAL_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_USER", "admin")
    monkeypatch.setenv("TECH_PASSWORD_HASH", S3CRET_HASH)
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://unused")
    monkeypatch.setenv("OPENROUTER_API_KEY", "unused")
    app = create_app(load_env=False)
    job = EvalJob(fake_work)
    app.dependency_overrides[get_eval_job] = lambda: job
    return TestClient(app)


def test_start_checks_model_and_scenarios(client):
    assert (
        client.post("/api/eval/start", json={"model": "openai/gpt-5.6-luna", "scenario_ids": ["mood-01"]}).status_code
        == 401
    )
    client.post("/api/admin/login", json={"name": "admin", "password": "s3cret"})
    assert client.post("/api/eval/start", json={"model": "x/y", "scenario_ids": ["mood-01"]}).status_code == 422
    bad = client.post("/api/eval/start", json={"model": "openai/gpt-5.6-luna", "scenario_ids": ["nope"]})
    assert bad.status_code == 422


def test_options_list_models_with_prices_scenarios_and_presets(client, monkeypatch):
    from cinesense.web_api import eval_view

    class Prices:
        def prices(self):
            return {"openai/gpt-5.6-luna": (0.3e-6, 1.5e-6)}

    monkeypatch.setattr(eval_view, "get_price_list", lambda: Prices())
    client.post("/api/admin/login", json={"name": "admin", "password": "s3cret"})
    d = client.get("/api/eval/options").json()
    luna = next(m for m in d["models"] if m["id"] == "openai/gpt-5.6-luna")
    assert luna["input_per_million"] == 0.3 and luna["price_source"] == "openrouter"
    haiku = next(m for m in d["models"] if m["id"] == "anthropic/claude-haiku-5.5")
    assert haiku["price_source"] == "table" and haiku["input_per_million"] == 0.1
    ids = {s["id"] for s in d["scenarios"]}
    assert set(d["presets"]["quick"]) <= ids and set(d["presets"]["medium"]) <= ids
    assert len(d["presets"]["all"]) == len(ids)
