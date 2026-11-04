from cinesense.eval.runner import PRICES, cost_usd, run_scenarios, summarise
from cinesense.eval.scenarios import Expect, Scenario


def movie(title, runtime=100):
    return {
        "movie": {
            "title": title,
            "runtime_min": runtime,
            "genres": [],
            "kind": "film",
            "year": 2000,
            "directors": [],
            "cast_top": [],
            "availability": {},
        },
        "reasons": [],
    }


def ok_runner(failure):
    def run(thread_id, message, criteria, on_status=None, profile=None):
        return {
            "reply": f"**Film {message}**",
            "criteria": {**criteria, "seen": message},
            "results": [movie(f"Film {message}")],
            "tools_called": ["set_mood_tags"],
            "usage": {"input_tokens": 1000, "output_tokens": 100},
        }

    return run


def test_multi_turn_scenario_passes_and_carries_criteria():
    seen = []

    def make(failure):
        inner = ok_runner(failure)

        def run(thread_id, message, criteria, on_status=None, profile=None):
            seen.append((thread_id, dict(criteria)))
            return inner(thread_id, message, criteria)

        return run

    s = Scenario(id="s1", category="mood", turns=["a", "b"], expect=Expect(tools_any=["set_mood_tags"]))
    [res] = run_scenarios([s], make, {"Film a", "Film b"})
    assert res["passed"] and res["error"] is None and res["tools_called"] == ["set_mood_tags", "set_mood_tags"]
    assert seen[0][0] == seen[1][0] and seen[1][1]["seen"] == "a"
    assert res["input_tokens"] == 2000 and res["cost_usd"] > 0


def test_failing_turn_is_recorded_and_the_run_continues():
    def make(failure):
        if failure == "streaming_down":

            def boom(*a, **k):
                raise TimeoutError("upstream timeout")

            return boom
        return ok_runner(failure)

    s1 = Scenario(id="bad", category="failure", failure="streaming_down", turns=["x"])
    s2 = Scenario(id="good", category="mood", turns=["y"])
    bad, good = run_scenarios([s1, s2], make, set())
    assert not bad["passed"] and "upstream timeout" in bad["error"] and good["passed"]


def test_missing_usage_is_flagged_not_fatal():
    def make(failure):
        def run(*a, **k):
            return {"reply": "x", "criteria": {}, "results": [movie("Z")], "tools_called": []}

        return run

    [res] = run_scenarios([Scenario(id="u", category="mood", turns=["q"])], make, set())
    assert res["input_tokens"] == 0 and res["usage_missing"] and res["cost_usd"] == 0


def test_cost_uses_openrouter_prices():
    assert (
        cost_usd({"input_tokens": 1_000_000, "output_tokens": 1_000_000}, PRICES["anthropic/claude-haiku-5.5"]) == 0.6
    )


def test_summary_rates():
    def make(failure):
        return ok_runner(failure)

    res = run_scenarios(
        [
            Scenario(id=f"s{i}", category="mood", turns=["q"], expect=Expect(max_runtime=90 if i else None))
            for i in range(2)
        ],
        make,
        {"Film q"},
    )
    s = summarise(res)
    assert s["scenarios"] == 2 and s["constraint_satisfaction"] == 0.0 and s["tool_selection"] is None
    assert s["tool_success"] == 1.0
    assert s["counts"]["constraint_satisfaction"] == [0, 1]  # only the scenario with a constraint applies
    assert s["counts"]["reply_checks"] == [0, 0]


def test_raw_grounding_counts_fallbacks_and_zero_tokens_flag_usage():
    def make(failure):
        def run(*a, **k):
            return {
                "reply": "Here are films that match:",
                "criteria": {},
                "results": [movie("Z")],
                "tools_called": [],
                "grounding_fallback": True,
                "grounding_reason": ["Titanic"],
                "usage": {"input_tokens": 0, "output_tokens": 0},
            }

        return run

    res = run_scenarios([Scenario(id="g", category="mood", turns=["q"])], make, set())
    s = summarise(res)
    assert res[0]["usage_missing"] and res[0]["grounding_reason"] == ["Titanic"]
    assert s["grounding"] == 1.0 and s["grounding_raw"] == 0.0


def test_relaxation_rate_counts_only_scenarios_with_a_rule():
    res = run_scenarios(
        [
            Scenario(id="r1", category="relaxation", turns=["q"], expect=Expect(relaxed=True)),
            Scenario(id="r2", category="relaxation", turns=["q"], expect=Expect(relaxed=False)),
            Scenario(id="m", category="mood", turns=["q"]),
        ],
        ok_runner,
        {"Film q"},
    )
    s = summarise(res)
    assert s["relaxation"] == 0.5 and s["counts"]["relaxation"] == [1, 2]
    assert res[0]["relaxed"] == [] and res[0]["checks"]["relaxed"]["why"] == ["expected a widened search"]


def test_report_lists_the_relaxation_row():
    from cinesense.eval.report import ROWS

    assert ("relaxation", "Search widening — widened exactly when the scenario expects it") in ROWS


def test_guard_rate_counts_only_scenarios_with_a_rule():
    def guarding_runner(failure):
        run = ok_runner(failure)
        return lambda thread, message, criteria, *a: {**run(thread, message, criteria), "guarded": "ignore" in message}

    res = run_scenarios(
        [
            Scenario(
                id="i1", category="injection", turns=["ignore all"], expect=Expect(guarded=True, results_required=False)
            ),
            Scenario(id="i2", category="injection", turns=["a film about an AI"], expect=Expect(guarded=False)),
            Scenario(
                id="i3", category="injection", turns=["print it"], expect=Expect(guarded=True, results_required=False)
            ),
            Scenario(id="m", category="mood", turns=["q"]),
        ],
        guarding_runner,
        {"Film q"},
    )
    s = summarise(res)
    assert s["guard"] == round(2 / 3, 3) and s["counts"]["guard"] == [2, 3]
    assert res[0]["guarded"] is True and res[2]["checks"]["guarded"]["why"] == ["attack reached the model"]


def test_report_lists_the_guard_row():
    from cinesense.eval.report import ROWS

    assert "guard" in dict(ROWS)


def test_a_blocked_turn_without_tokens_is_not_missing_usage():
    def blocking_runner(failure):
        return lambda *a, **k: {"reply": "blocked", "criteria": {}, "results": [], "guarded": True, "usage": {}}

    res = run_scenarios(
        [Scenario(id="i", category="injection", turns=["x"], expect=Expect(guarded=True, results_required=False))],
        blocking_runner,
        set(),
    )
    assert res[0]["usage_missing"] is False
