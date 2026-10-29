"""Markdown report for the evaluation run (eval/REPORT.md). Every rate is shown with its k/n."""

import statistics

ROWS = [
    (
        "constraint_satisfaction",
        "Constraint satisfaction — scenarios with a runtime/genre/kind/year/person/availability rule",
    ),
    ("tool_selection", "Tool selection — an expected tool was called (scenarios that name tools)"),
    ("reply_checks", "Factual reply checks — expected fact in the answer"),
    ("availability_claims", "No streaming claim without known availability"),
    ("grounding", "Grounding after the guard — reply names only returned or user-named films"),
]


def _pct(v) -> str:
    return "—" if v is None else f"{100 * v:.0f}%"


def _mean(xs: list) -> str:
    xs = [x for x in xs if x is not None]
    return f"{statistics.mean(xs):.2f}" if xs else "—"


def render_report(summary: dict, results: list[dict], comparison: dict, date: str, model: str = "") -> str:
    counts = summary.get("counts", {})
    out = [f"# CineSense evaluation — {date}", ""]
    out += [
        f"{summary['scenarios']} scenarios, {summary['passed']} passed all automatic checks, "
        f"{summary['errors']} errored. Agent model: {model or 'see config'} via OpenRouter. "
        "Streaming data comes from the cache only (no API budget spent).",
        "",
        "## Automatic metrics",
        "",
        "| Metric | Result |",
        "|---|---|",
    ]
    for key, label in ROWS:
        k, n = counts.get(key, [None, None])
        out.append(f"| {label} | {_pct(summary.get(key))} ({k}/{n}) |")
    fallbacks = summary["grounding_fallbacks"]
    out += [
        f"| Grounding before the guard — no template fallback needed | {_pct(summary.get('grounding_raw'))} "
        f"({fallbacks} fallbacks) |",
        f"| Tool calls that raised no error | {_pct(summary['tool_success'])} |",
        f"| Latency per scenario, median / p90 | {summary['latency_median_s']} s / {summary['latency_p90_s']} s |",
        f"| Cost per chat turn | ${summary['cost_per_turn_usd']:.4f} |",
        f"| Cost of all agent turns | ${summary['cost_total_usd']:.3f} |",
        f"| Scenarios with missing token usage | {summary.get('usage_missing', 0)} |",
        "",
        "Caveats: the checks are deliberately narrow — a scenario without a rule for a metric is not counted in it. "
        "Tool errors count only exceptions; a degraded source (e.g. embeddings down) still returns a result.",
        "",
        "## Relevance — LLM judge (Claude Sonnet 5.5)",
        "",
        "Subjective: the judge rates the agent's top 5 for each scenario on 1–5 from titles and years only "
        "(which likely favours well-known films). Not an automatic metric.",
        "",
    ]
    scores = [r.get("judge", {}).get("score") for r in results]
    out += [f"Mean judge score over {sum(s is not None for s in scores)} scenarios: **{_mean(scores)}** / 5", ""]
    rows = comparison.get("rows", [])
    if rows:
        out += [
            "## Ranking comparison",
            "",
            f"{len(rows)} scenarios with mood tags. Same criteria (as set by the agent) and the same hard filters for "
            "all three rankers; plot and person signals are left out of the comparison because the baselines have "
            "none. *Tag relevance* is the weighted mean relevance of the requested tags — CineSense's own ranking "
            "objective; *tag cosine* is movieFinder's objective. Each ranker is favoured by its own metric, so read "
            "them together with the judge.",
            "",
            "| Ranker | Tag relevance@10 | Tag cosine@10 | Median rating count | Constraints OK | LLM judge |",
            "|---|---|---|---|---|---|",
        ]
        for name in ("bayesian", "cosine", "cinesense"):
            m = [r["metrics"][name] for r in rows]
            cnt = [x["median_rating_count"] for x in m if x["median_rating_count"]]
            known = [x["constraint_ok"] for x in m if x["constraint_ok"] is not None]
            title = {
                "bayesian": "Baseline A: filters + Bayesian rating",
                "cosine": "Baseline B: movieFinder cosine",
                "cinesense": "CineSense",
            }[name]
            med = int(statistics.median(cnt)) if cnt else "—"
            ok_mean = statistics.mean(known) if known else None
            out.append(
                f"| {title} | {_mean([x['tag_relevance'] for x in m])} | {_mean([x.get('tag_cosine') for x in m])} "
                f"| {med} | {_pct(ok_mean)} | {_mean([r['judge'].get(name) for r in rows])} |"
            )
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
    out += ["", "## Template fallbacks", ""]
    fb = [r for r in results if r.get("grounding_fallback")]
    out += [f"- **{r['id']}**: {', '.join(r.get('grounding_reason') or ['(reason not recorded)'])}" for r in fb] or [
        "None."
    ]
    out += ["", "## Failures", ""]
    failed = [r for r in results if not r["passed"]]
    if not failed:
        out.append("None.")
    for r in failed:
        why = [w for c in r["checks"].values() for w in c["why"]] + ([r["error"]] if r["error"] else [])
        out.append(f"- **{r['id']}**: " + "; ".join(why[:4]))
    return "\n".join(out) + "\n"
