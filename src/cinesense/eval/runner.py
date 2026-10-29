"""Run scenarios through a chat runner (the real agent or a fake) and score them automatically."""

import statistics
import time
import uuid
from collections.abc import Callable

from cinesense.eval.checks import check_constraints, check_grounding, check_reply, check_tools, title_hit
from cinesense.eval.scenarios import Scenario

# USD per token, from https://openrouter.ai/api/v1/models (checked 2026-10-29)
PRICES = {
    "anthropic/claude-haiku-5.5": (0.10e-6, 0.50e-6),
    "anthropic/claude-sonnet-5.5": (2.0e-6, 10.0e-6),
}


def cost_usd(usage: dict, price: tuple[float, float]) -> float:
    return round(usage.get("input_tokens", 0) * price[0] + usage.get("output_tokens", 0) * price[1], 6)


def run_scenarios(
    scenarios: list[Scenario],
    make_runner: Callable,
    catalogue_titles: set[str],
    model: str = "anthropic/claude-haiku-5.5",
    tag_names: list[str] = (),
) -> list[dict]:
    out = []
    for s in scenarios:
        runner = make_runner(s.failure)
        thread, criteria = f"eval-{s.id}-{uuid.uuid4().hex[:8]}", dict(s.ui_criteria)
        res = {
            "id": s.id,
            "category": s.category,
            "failure": s.failure,
            "turns": s.turns,
            "tools_called": [],
            "tool_errors": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "usage_missing": False,
            "latency_s": 0.0,
            "error": None,
        }
        last: dict = {}
        try:
            for turn in s.turns:
                t0 = time.perf_counter()
                last = runner(thread, turn, criteria)
                res["latency_s"] += time.perf_counter() - t0
                criteria = last.get("criteria") or criteria
                res["tools_called"] += last.get("tools_called", [])
                res["tool_errors"] += last.get("tool_errors", 0)
                usage = last.get("usage") or {}
                res["usage_missing"] |= not usage
                res["input_tokens"] += usage.get("input_tokens", 0)
                res["output_tokens"] += usage.get("output_tokens", 0)
        except Exception as exc:  # noqa: BLE001 — one broken scenario must not stop the evaluation
            res["error"] = f"{type(exc).__name__}: {exc}"[:300]
        results, reply = last.get("results", []), last.get("reply", "")
        checks = {
            "constraints": check_constraints(results, s.expect),
            "tools": check_tools(res["tools_called"], s.expect),
            "grounding": check_grounding(reply, results, catalogue_titles, " ".join(s.turns), tag_names),
            "reply": check_reply(reply, s.expect),
        }
        res.update(
            reply=reply,
            results=[r["movie"]["title"] for r in results],
            top=[{"title": r["movie"]["title"], "year": r["movie"].get("year")} for r in results[:5]],
            criteria=criteria,
            grounding_fallback=last.get("grounding_fallback", False),
            checks={k: {"ok": ok, "why": why} for k, (ok, why) in checks.items()},
            title_hit=title_hit(results, s.expect),
            passed=res["error"] is None and all(ok for ok, _ in checks.values()),
            latency_s=round(res["latency_s"], 2),
        )
        res["cost_usd"] = cost_usd(res, PRICES[model])
        out.append(res)
    return out


def _rate(items: list[bool]) -> float | None:
    return round(sum(items) / len(items), 3) if items else None


def summarise(results: list[dict]) -> dict:
    ok = [r for r in results if r["error"] is None]
    hits = [r["title_hit"] for r in results if r["title_hit"] is not None]
    lat = [r["latency_s"] for r in ok]
    return {
        "scenarios": len(results),
        "passed": sum(r["passed"] for r in results),
        "errors": len(results) - len(ok),
        "constraint_satisfaction": _rate([r["checks"]["constraints"]["ok"] for r in ok]),
        "tool_selection": _rate([r["checks"]["tools"]["ok"] for r in ok]),
        "tool_success": round(
            1 - sum(r["tool_errors"] for r in ok) / max(1, sum(len(r["tools_called"]) for r in ok)), 3
        ),
        "grounding": _rate([r["checks"]["grounding"]["ok"] for r in ok]),
        "grounding_fallbacks": sum(bool(r.get("grounding_fallback")) for r in ok),
        "reply_checks": _rate([r["checks"]["reply"]["ok"] for r in ok]),
        "title_hit_rate": _rate(hits),
        "latency_median_s": round(statistics.median(lat), 2) if lat else None,
        "latency_p90_s": round(sorted(lat)[int(0.9 * (len(lat) - 1))], 2) if lat else None,
        "cost_total_usd": round(sum(r["cost_usd"] for r in results), 4),
        "cost_per_turn_usd": round(
            sum(r["cost_usd"] for r in results) / max(1, sum(len(r["turns"]) for r in results)), 5
        ),
        "usage_missing": sum(r["usage_missing"] for r in results),
    }
