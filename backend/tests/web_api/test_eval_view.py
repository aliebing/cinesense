"""GET /api/eval/runs[/{run}]: the evaluation results for the login-protected /tech/eval page."""

import json

import pytest
from fastapi.testclient import TestClient

from cinesense.web_api.app import create_app


def scenario(id_, passed, judge):
    return {
        "id": id_,
        "category": "mood",
        "turns": ["x"],
        "passed": passed,
        "judge": {"score": judge, "reason": "ok"},
        "checks": {"tools": {"ok": passed, "why": [], "applies": True}},
    }


def run_file(scenarios, rows):
    return {
        "summary": {"scenarios": len(scenarios), "passed": sum(s["passed"] for s in scenarios)},
        "results": scenarios,
        "comparison": {"rows": rows, "judge_cost_usd": 0.2},
    }


ROW = {
    "id": "a",
    "metrics": {"cinesense": {"tag_relevance": 0.8}, "cosine": {"tag_relevance": 0.6}},
    "judge": {"cinesense": 4, "cosine": 3},
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CINESENSE_EVAL_DIR", str(tmp_path))
    monkeypatch.delenv("TECH_USER", raising=False)
    monkeypatch.delenv("TECH_PASSWORD", raising=False)
    (tmp_path / "2026-11-01_1000.json").write_text(json.dumps(run_file([scenario("a", True, 4)], [ROW])))
    (tmp_path / "2026-11-02_1000.json").write_text(
        json.dumps(run_file([scenario("a", True, 5), scenario("b", False, None), scenario("c", True, 2)], [ROW, ROW]))
    )
    (tmp_path / "notes.txt").write_text("not a run")
    return TestClient(create_app(load_env=False))


def test_runs_are_listed_oldest_first_with_their_means(client):
    runs = client.get("/api/eval/runs").json()
    assert [r["run"] for r in runs] == ["2026-11-01_1000", "2026-11-02_1000"]
    last = runs[-1]
    assert last["scenarios"] == 3 and last["passed"] == 2
    assert last["agent_judge"] == 3.5  # mean of the scored scenarios only
    assert last["ranker_judge"] == {"cinesense": 4.0, "cosine": 3.0}


def test_one_run_with_ranker_means(client):
    d = client.get("/api/eval/runs/2026-11-02_1000").json()
    assert d["run"] == "2026-11-02_1000" and len(d["results"]) == 3
    assert d["rankers"]["cinesense"] == {"judge": 4.0, "tag_relevance": 0.8}
    assert d["comparison"]["judge_cost_usd"] == 0.2


def test_unknown_or_malformed_run_is_404(client):
    assert client.get("/api/eval/runs/2026-01-01_0000").status_code == 404
    assert client.get("/api/eval/runs/..%2F..%2Fetc").status_code == 404


def test_eval_needs_the_tech_login_when_one_is_configured(client, monkeypatch):
    monkeypatch.setenv("TECH_USER", "admin")
    monkeypatch.setenv("TECH_PASSWORD", "s3cret")
    assert client.get("/api/eval/runs").status_code == 401
    client.post("/api/admin/login", json={"name": "admin", "password": "s3cret"})
    assert client.get("/api/eval/runs").status_code == 200
