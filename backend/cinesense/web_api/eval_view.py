"""Evaluation endpoints for the login-protected /admin/evaluation page.

Saved runs: GET /api/eval/runs (history, oldest first) and /api/eval/runs/{run} (one run in full), read from
CINESENSE_EVAL_DIR (the `make eval` runs shipped with a deploy) and CINESENSE_EVAL_RUNS_DIR (runs started on the
page, written by the API).

Running: GET /api/eval/options (models with live OpenRouter prices and a cost estimate, scenarios, presets),
POST /api/eval/start, GET /api/eval/live (the running run, polled), POST /api/eval/stop."""

import json
import re
import statistics
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from cinesense.chat_agent.llm import PRICES
from cinesense.core.config import get_settings
from cinesense.evaluation.scenarios import load_scenarios
from cinesense.evaluation.session import COMPARE, JUDGE_MODEL, MODELS, PRESETS
from cinesense.web_api.admin_session import require_tech_login
from cinesense.web_api.eval_jobs import Busy, EvalJob

router = APIRouter(dependencies=[Depends(require_tech_login)])
RUN_ID = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{4}(\d{2})?$")  # the file name a run is saved under (guards the path)


def _mean(values) -> float | None:
    vals = [v for v in values if isinstance(v, int | float)]
    return round(statistics.mean(vals), 2) if vals else None


def _folders() -> list[Path]:
    s = get_settings()
    return list(dict.fromkeys([s.eval_dir, s.eval_runs_dir]))


def _runs() -> dict[str, Path]:
    found: dict[str, Path] = {}
    for folder in _folders():
        if folder.is_dir():
            for p in folder.glob("*.json"):
                if RUN_ID.match(p.stem):
                    found.setdefault(p.stem, p)
    return dict(sorted(found.items()))


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
    comparison = data.get("comparison") or {}
    rows = comparison.get("rows", [])
    scenarios = s.get("scenarios", len(results))
    return {
        "run": run,
        "scenarios": scenarios,
        "scenarios_total": s.get("scenarios_total", scenarios),  # runs before 2026-11-05 always ran every scenario
        "passed": s.get("passed", sum(bool(r.get("passed")) for r in results)),
        "grounding_raw": s.get("grounding_raw"),
        "agent_judge": _mean((r.get("judge") or {}).get("score") for r in results),
        "ranker_judge": {n: v["judge"] for n, v in _rankers(rows).items()},
        "model": s.get("agent_model"),
        "cost_usd": round((s.get("cost_total_usd") or 0) + (comparison.get("judge_cost_usd") or 0), 4),
        "stopped": bool(s.get("stopped")),
        "source": s.get("source", "local"),
    }


@router.get("/api/eval/runs")
def list_runs() -> list[dict]:
    """Every saved run, oldest first, with the numbers the history and the run list show."""
    return [_overview(name, _load(p)) for name, p in _runs().items()]


@router.get("/api/eval/runs/{run}")
def get_run(run: str) -> dict:
    path = _runs().get(run) if RUN_ID.match(run) else None
    if path is None:
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


# --- running an evaluation ------------------------------------------------------------------------------------


@lru_cache
def get_price_list():
    from cinesense.data_sources.openrouter import PriceList

    return PriceList()


def _usage_basis() -> dict | None:
    """Token use per scenario and judge cost per judge call, from the latest run with at least 30 scenarios."""
    for _name, path in reversed(_runs().items()):
        data = _load(path)
        results = data.get("results", [])
        if len(results) < 30:
            continue
        rows = (data.get("comparison") or {}).get("rows", [])
        calls = len(results) + 3 * len(rows)
        return {
            "input_tokens": statistics.mean(r.get("input_tokens", 0) for r in results),
            "output_tokens": statistics.mean(r.get("output_tokens", 0) for r in results),
            "judge_per_call": ((data.get("comparison") or {}).get("judge_cost_usd") or 0) / max(1, calls),
            "measured_with": (data.get("summary") or {}).get("agent_model") or "anthropic/claude-haiku-5.5",
        }
    return None


def _price(model: str, live: dict) -> tuple[tuple[float, float], str]:
    if model in live:
        return live[model], "openrouter"
    return PRICES.get(model, (0.0, 0.0)), "table"


@router.get("/api/eval/options")
def options() -> dict:
    live = get_price_list().prices()
    basis = _usage_basis()
    scenarios = load_scenarios()
    models = []
    for model_id, label in MODELS.items():
        (pin, pout), source = _price(model_id, live)
        entry = {
            "id": model_id,
            "label": label,
            "input_per_million": round(pin * 1e6, 4),
            "output_per_million": round(pout * 1e6, 4),
            "price_source": source,
            "agent_per_scenario_usd": None,
        }
        if basis:
            entry["agent_per_scenario_usd"] = round(basis["input_tokens"] * pin + basis["output_tokens"] * pout, 6)
        models.append(entry)
    (jin, jout), jsource = _price(JUDGE_MODEL, live)
    return {
        "models": models,
        "default_model": get_settings().llm_model,
        "judge": {
            "id": JUDGE_MODEL,
            "label": MODELS.get(JUDGE_MODEL, JUDGE_MODEL),
            "input_per_million": round(jin * 1e6, 4),
            "output_per_million": round(jout * 1e6, 4),
            "price_source": jsource,
            "per_call_usd": round(basis["judge_per_call"], 6) if basis else None,
        },
        "estimate_basis": basis and basis["measured_with"],
        "scenarios": [
            {"id": s.id, "category": s.category, "turns": s.turns, "compared": s.category in COMPARE} for s in scenarios
        ],
        "presets": {**PRESETS, "all": [s.id for s in scenarios]},
    }


def _work(model: str, scenario_ids: list[str], on_progress, should_stop) -> str:
    """One run on the server: the shared catalogue, embeddings and cache-only streaming, saved to the runs folder."""
    from cinesense.evaluation.session import cache_only_streaming, run_evaluation, run_stamp, save_run
    from cinesense.web_api.deps import get_embedder, get_provider

    s = get_settings()
    by_id = {sc.id: sc for sc in load_scenarios()}
    live = get_price_list().prices()
    data = run_evaluation(
        [by_id[i] for i in scenario_ids],
        settings=s,
        provider=get_provider(),
        embedder=get_embedder(),
        streaming=cache_only_streaming(s),
        model=model,
        price=_price(model, live)[0],
        judge_price=_price(JUDGE_MODEL, live)[0],
        on_progress=on_progress,
        should_stop=should_stop,
        scenarios_total=len(by_id),
        source="server",
    )
    return save_run(data, s.eval_runs_dir, run_stamp()).stem


@lru_cache
def get_eval_job() -> EvalJob:
    return EvalJob(_work)


class StartRequest(BaseModel):
    model: str
    scenario_ids: list[str] = Field(min_length=1, max_length=200)


@router.post("/api/eval/start")
def start(req: StartRequest, job: EvalJob = Depends(get_eval_job)) -> dict:  # noqa: B008
    if req.model not in MODELS:
        raise HTTPException(status_code=422, detail="unknown model")
    known = {s.id for s in load_scenarios()}
    if unknown := [i for i in req.scenario_ids if i not in known]:
        raise HTTPException(status_code=422, detail=f"unknown scenarios: {', '.join(unknown[:5])}")
    s = get_settings()
    if not (s.database_url and s.openrouter_api_key):
        raise HTTPException(status_code=503, detail="needs the catalogue database and an OpenRouter key")
    try:
        return job.start(req.model, list(dict.fromkeys(req.scenario_ids)))
    except Busy:
        raise HTTPException(status_code=409, detail="a run is already going") from None


@router.get("/api/eval/live")
def live(job: EvalJob = Depends(get_eval_job)) -> dict:  # noqa: B008
    return job.snapshot()


@router.post("/api/eval/stop")
def stop(job: EvalJob = Depends(get_eval_job)) -> dict:  # noqa: B008
    return job.stop()
