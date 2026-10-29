from cinesense.agent.graph import run_turn
from cinesense.domain.criteria import SearchCriteria

from .conftest import ai


def empty():
    return SearchCriteria().model_dump()


def test_react_loop_sets_criteria_then_presents(make_agent):
    g = make_agent([ai(calls=[("set_mood_tags", {"tags": [{"name": "space travel", "weight": 9}]})]), ai("Done.")])
    out = run_turn(g, "t1", "something in space", empty())
    assert out["criteria"]["tags"] and out["results"]
    assert out["reply"]


def test_clarifying_question_ends_without_present(make_agent):
    g = make_agent([ai("Do you mean space, feelings or scientific puzzles?")])
    out = run_turn(g, "t2", "something like Interstellar", empty())
    assert out["results"] == [] and out["reply"].startswith("Do you mean")


def test_loop_stops_after_6_rounds(make_agent):
    looping = [ai(calls=[("set_filters", {"max_runtime_min": 120})]) for _ in range(10)]
    g = make_agent(looping)
    out = run_turn(g, "t3", "keep going", empty())
    assert out["rounds"] == 6 and out["results"]


def test_ui_criteria_seed_the_turn(make_agent):
    ui = SearchCriteria(person="Keanu Reeves").model_dump()
    g = make_agent([ai(calls=[("set_filters", {"max_runtime_min": 150})]), ai("ok")])
    out = run_turn(g, "t4", "shorter please", ui)
    assert out["criteria"]["person"] == "Keanu Reeves" and out["criteria"]["max_runtime_min"] == 150


def test_thread_memory_keeps_history(make_agent):
    g = make_agent([ai("First?"), ai("Second.")])
    run_turn(g, "t5", "hi", empty())
    out = run_turn(g, "t5", "again", empty())
    assert out["history_len"] >= 4


def test_parallel_tool_calls_apply_in_order(make_agent):
    calls = [
        ("set_mood_tags", {"tags": [{"name": "dark", "weight": 8}]}),
        ("set_filters", {"max_runtime_min": 130}),
        ("set_mood_tags", {"tags": [{"name": "horror", "mode": "not"}]}),
    ]
    g = make_agent([ai(calls=calls), ai("Done.")])
    out = run_turn(g, "t6", "dark, short, no horror", empty())
    assert len(out["criteria"]["tags"]) == 2 and out["criteria"]["max_runtime_min"] == 130


def test_failing_tool_reports_error_to_model(make_agent):
    g = make_agent([ai(calls=[("set_mood_tags", {"tags": "not-a-list"})]), ai("Sorry.")])
    out = run_turn(g, "t7", "x", empty())
    assert out["reply"] == "Sorry."
