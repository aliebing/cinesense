"""Markdown report for the evaluation run (eval/REPORT.md)."""

import statistics

LABELS = {
    "constraint_satisfaction": "Constraint satisfaction (results obey runtime/genre/kind/year/person/availability)",
    "tool_selection": "Tool selection (an expected tool was called)",
    "tool_success": "Tool success rate (tool calls without error)",
    "grounding": "Grounding (reply names only returned or user-named films)",
    "reply_checks": "Factual reply checks (expected facts in the answer)",
    "title_hit_rate": "Known-good title among the results (where defined)",
}


def _pct(v) -> str:
    return "—" if v is None else f"{100 * v:.0f}%"


def _mean(xs: list) -> str:
    xs = [x for x in xs if x is not None]
    return f"{statistics.mean(xs):.2f}" if xs else "—"


def render_report(summary: dict, results: list[dict], comparison: dict, date: str) -> str:
    out = [f"# CineSense evaluation — {date}", ""]
    out += [
        f"{summary['scenarios']} scenarios, {summary['passed']} passed all automatic checks, "
        f"{summary['errors']} errored. Agent model: Claude Haiku 5.5 via OpenRouter.",
        "",
        "## Automatic metrics",
        "",
        "| Metric | Value |",
        "|---|---|",
    ]
    out += [f"| {label} | {_pct(summary[k])} |" for k, label in LABELS.items()]
    out += [
        f"| Grounding fallbacks (template answer used) | {summary['grounding_fallbacks']} |",
        f"| Latency per scenario, median / p90 | {summary['latency_median_s']} s / {summary['latency_p90_s']} s |",
        f"| Cost per chat turn | ${summary['cost_per_turn_usd']:.4f} |",
        f"| Cost of all agent turns | ${summary['cost_total_usd']:.3f} |",
        "",
        "## Relevance — LLM judge (Claude Sonnet 5.5)",
        "",
        "Subjective: the judge rates the agent's top 5 for each scenario on 1–5. Not an automatic metric.",
        "",
    ]
    scores = [r.get("judge", {}).get("score") for r in results]
    out += [f"Mean judge score over {sum(s is not None for s in scores)} scenarios: **{_mean(scores)}** / 5", ""]
    rows = comparison.get("rows", [])
    if rows:
        out += [
            "## Ranking comparison",
            "",
            "Same criteria (as set by the agent) and the same hard filters for all three rankers. "
            "Tag relevance = mean Tag Genome relevance of the requested tags in the top 10 (automatic). "
            "Median rating count = how well-known the picks are. Judge = LLM judge (Claude Sonnet 5.5) on the top 5.",
            "",
            "| Ranker | Tag relevance@10 | Median rating count | Constraints OK | LLM judge |",
            "|---|---|---|---|---|",
        ]
        for name in ("bayesian", "cosine", "cinesense"):
            rel = [r["metrics"][name]["tag_relevance"] for r in rows]
            cnt = [r["metrics"][name]["median_rating_count"] for r in rows if r["metrics"][name]["median_rating_count"]]
            ok = [r["metrics"][name]["constraint_ok"] for r in rows]
            jd = [r["judge"].get(name) for r in rows]
            title = {
                "bayesian": "Baseline A: filters + Bayesian rating",
                "cosine": "Baseline B: movieFinder cosine",
                "cinesense": "CineSense",
            }[name]
            med = int(statistics.median(cnt)) if cnt else "—"
            known = [x for x in ok if x is not None]
            ok_mean = statistics.mean(known) if known else None
            out.append(f"| {title} | {_mean(rel)} | {med} | {_pct(ok_mean)} | {_mean(jd)} |")
        out += ["", f"Judge cost for the comparison: ${comparison.get('judge_cost_usd', 0):.3f}", ""]
    out += [
        "## Per scenario",
        "",
        "| Scenario | Category | Passed | Judge | Latency | Top results |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        top = ", ".join(r["results"][:3]) or "—"
        js = r.get("judge", {}).get("score")
        mark = "✅" if r["passed"] else "❌"
        out.append(f"| {r['id']} | {r['category']} | {mark} | {js or '—'} | {r['latency_s']} s | {top} |")
    out += ["", "## Failures", ""]
    failed = [r for r in results if not r["passed"]]
    if not failed:
        out.append("None.")
    for r in failed:
        why = [w for c in r["checks"].values() for w in c["why"]] + ([r["error"]] if r["error"] else [])
        out.append(f"- **{r['id']}**: " + "; ".join(why[:4]))
    return "\n".join(out) + "\n"
