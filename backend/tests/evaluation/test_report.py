from cinesense.evaluation.report import render_report


def test_report_has_all_sections_and_labels_the_judge():
    summary = {
        "scenarios": 2,
        "passed": 1,
        "errors": 0,
        "constraint_satisfaction": 0.5,
        "tool_selection": 1.0,
        "tool_success": 1.0,
        "grounding": 1.0,
        "grounding_fallbacks": 0,
        "reply_checks": 1.0,
        "title_hit_rate": None,
        "latency_median_s": 9.1,
        "latency_p90_s": 14.0,
        "cost_total_usd": 0.01,
        "cost_per_turn_usd": 0.005,
        "usage_missing": 0,
        "grounding_raw": 0.8,
        "availability_claims": 1.0,
        "counts": {
            "constraint_satisfaction": [0, 1],
            "tool_selection": [1, 1],
            "reply_checks": [0, 0],
            "grounding": [1, 1],
            "availability_claims": [1, 1],
        },
    }
    results = [
        {
            "id": "mood-01",
            "category": "mood",
            "passed": False,
            "error": None,
            "results": ["Moon"],
            "checks": {
                "constraints": {"ok": False, "why": ["X: 150 min > 120"]},
                "tools": {"ok": True, "why": []},
                "grounding": {"ok": True, "why": []},
                "reply": {"ok": True, "why": []},
            },
            "judge": {"score": 4, "reason": "good"},
            "latency_s": 9.1,
            "cost_usd": 0.001,
        }
    ]
    comparison = {
        "rows": [
            {
                "id": "mood-01",
                "metrics": {
                    "bayesian": {"tag_relevance": 0.3, "median_rating_count": 50000, "constraint_ok": 1.0},
                    "cosine": {"tag_relevance": 0.5, "median_rating_count": 300, "constraint_ok": 1.0},
                    "cinesense": {"tag_relevance": 0.8, "median_rating_count": 9000, "constraint_ok": 1.0},
                },
                "judge": {"bayesian": 2, "cosine": 3, "cinesense": 4},
            }
        ],
        "judge_cost_usd": 0.2,
    }
    md = render_report(summary, results, comparison, "2026-10-29", "anthropic/claude-haiku-5.5")
    assert "(0/1)" in md and "own ranking objective" in md and "## Template fallbacks" in md
    for heading in ("## Automatic metrics", "## Relevance — LLM judge", "## Ranking comparison", "## Failures"):
        assert heading in md
    assert "LLM judge (Claude Sonnet 5.5)" in md and "X: 150 min > 120" in md and "0.80" in md
