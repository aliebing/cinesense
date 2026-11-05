"""GET /api/eval/runs and /api/eval/runs/{run}: the saved `make eval` runs (evaluation/results/*.json) for the
login-protected /tech/eval page — the history across runs and one run in full, with the means it charts.

Read-only; the directory is CINESENSE_EVAL_DIR (in the API container, mount the results there)."""

import json
import re
import statistics
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from cinesense.core.config import get_settings
from cinesense.web_api.inspect import require_tech_login

router = APIRouter(dependencies=[Depends(require_tech_login)])
RUN_ID = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{4}$")  # the file name `make eval` writes (also guards the path)


def _mean(values) -> float | None:
    vals = [v for v in values if isinstance(v, int | float)]
    return round(statistics.mean(vals), 2) if vals else None


def _runs(folder: Path) -> list[Path]:
    return sorted(p for p in folder.glob("*.json") if RUN_ID.match(p.stem)) if folder.is_dir() else []


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _rankers(rows: list[dict]) -> dict[str, dict]:
    names = sorted({n for r in rows for n in r.get("judge", {})})
    out = {}
    for n in names:
        entry = {"judge": _mean(r["judge"].get(n) for r in rows if "judge" in r)}
        metrics = {k for r in rows for k in (r.get("metrics", {}).get(n) or {})}
        for k in sorted(metrics):
            entry[k] = _mean((r.get("metrics", {}).get(n) or {}).get(k) for r in rows)
        out[n] = entry
    return out


def _overview(run: str, data: dict) -> dict:
    s, results = data.get("summary", {}), data.get("results", [])
    rows = (data.get("comparison") or {}).get("rows", [])
    return {
        "run": run,
        "scenarios": s.get("scenarios", len(results)),
        "passed": s.get("passed", sum(bool(r.get("passed")) for r in results)),
        "grounding_raw": s.get("grounding_raw"),
        "agent_judge": _mean((r.get("judge") or {}).get("score") for r in results),
        "ranker_judge": {n: v["judge"] for n, v in _rankers(rows).items()},
    }


@router.get("/api/eval/runs")
def list_runs() -> list[dict]:
    """Every saved run, oldest first, with the numbers the history charts show."""
    return [_overview(p.stem, _load(p)) for p in _runs(get_settings().eval_dir)]


@router.get("/api/eval/runs/{run}")
def get_run(run: str) -> dict:
    path = get_settings().eval_dir / f"{run}.json"
    if not RUN_ID.match(run) or not path.is_file():
        raise HTTPException(status_code=404, detail="unknown run")
    data = _load(path)
    rows = (data.get("comparison") or {}).get("rows", [])
    return {
        **_overview(run, data),
        "summary": data.get("summary", {}),
        "results": data.get("results", []),
        "comparison": data.get("comparison") or {},
        "rankers": _rankers(rows),
    }
