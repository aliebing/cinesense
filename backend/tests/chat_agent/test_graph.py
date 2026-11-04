from cinesense.chat_agent.graph import run_turn
from cinesense.core.criteria import SearchCriteria

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


def _all_calls_answered(g, thread):
    from langchain_core.messages import AIMessage, ToolMessage

    msgs = g.get_state({"configurable": {"thread_id": thread}}).values["messages"]
    calls = {c["id"] for m in msgs if isinstance(m, AIMessage) for c in m.tool_calls}
    answered = {m.tool_call_id for m in msgs if isinstance(m, ToolMessage)}
    return calls <= answered


def test_round_limit_with_read_only_tools_closes_all_calls(make_agent):
    looping = [ai(calls=[("film_facts", {"title": f"Alien {i}"})]) for i in range(10)]
    g = make_agent(looping)
    out = run_turn(g, "t8", "tell me about Alien and where I can watch it", empty())
    assert out["rounds"] == 6 and out["reply"].strip()
    assert _all_calls_answered(g, "t8")


def test_factual_answer_is_not_replaced_by_results(make_agent):
    g = make_agent([ai(calls=[("film_facts", {"title": "The Matrix"})]), ai("The Matrix is from 1999.")])
    out = run_turn(g, "t9", "Tell me more about the movie The Matrix", empty())
    assert out["reply"] == "The Matrix is from 1999." and out["results"] == []


def test_empty_model_reply_gets_a_default(make_agent):
    g = make_agent([ai("")])
    out = run_turn(g, "t10", "hm", empty())
    assert out["reply"].strip()


def test_concurrent_turns_on_one_thread_are_serialised(make_agent):
    import threading

    g = make_agent([ai("first"), ai("second")])
    outs = {}

    def turn(name):
        outs[name] = run_turn(g, "t11", name, empty())

    ts = [threading.Thread(target=turn, args=(n,)) for n in ("a", "b")]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert {outs["a"]["reply"], outs["b"]["reply"]} == {"first", "second"}
    assert outs["a"]["history_len"] != outs["b"]["history_len"]


def test_present_uses_the_profile(make_agent):
    from cinesense.data_sources.fixture import FixtureProvider
    from cinesense.taste.profile import Profile

    titanic = next(m.id for m in FixtureProvider().list_movies() if m.title == "Titanic")
    g = make_agent([ai(calls=[("set_filters", {"max_runtime_min": 300})]), ai("ok")])
    out = run_turn(g, "t12", "films", empty(), profile=Profile(disliked=[titanic]))
    assert out["results"] and titanic not in [r["movie"]["id"] for r in out["results"]]


def test_run_turn_reports_tools_and_tool_errors(make_agent):
    g = make_agent(
        [ai(calls=[("set_mood_tags", {"tags": [{"name": "dark"}]}), ("set_mood_tags", {"tags": "bad"})]), ai("ok")]
    )
    out = run_turn(g, "t13", "dark", empty())
    assert out["tools_called"] == ["set_mood_tags", "set_mood_tags"] and out["tool_errors"] == 1


def test_history_is_trimmed_at_turn_boundaries():
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

    from cinesense.chat_agent.graph import trim_history

    msgs = []
    for i in range(12):
        msgs += [
            HumanMessage(f"q{i}"),
            AIMessage("", tool_calls=[{"name": "t", "args": {}, "id": f"c{i}"}]),
            ToolMessage("ok", tool_call_id=f"c{i}"),
            AIMessage(f"a{i}"),
        ]
    kept = trim_history(msgs, max_turns=4)
    assert isinstance(kept[0], HumanMessage) and kept[0].content == "q8" and len(kept) == 16
    assert trim_history(msgs[:4], max_turns=4) == msgs[:4]


def test_turn_records_tool_calls_and_prompts_for_inspection(make_agent):
    g = make_agent([ai(calls=[("set_mood_tags", {"tags": [{"name": "space travel", "weight": 9}]})]), ai("Done.")])
    out = run_turn(g, "t10", "something in space", empty())
    call = out["tool_trace"][0]
    assert call["name"] == "set_mood_tags" and call["args"]["tags"][0]["name"] == "space travel"
    assert call["result"]  # the tool's answer to the model
    assert "CineSense" in out["prompts"]["agent"] and "Wish: something in space" in out["prompts"]["explain_input"]


def test_the_explanation_may_name_a_film_by_its_german_title():
    from langchain_core.messages import AIMessage
    from langgraph.checkpoint.memory import MemorySaver

    from cinesense.chat_agent.graph import build_graph
    from cinesense.chat_agent.tools import ToolKit, make_tools
    from cinesense.core.models import Movie
    from cinesense.data_sources.fixture import FixtureProvider
    from cinesense.search.service import SearchService

    from .conftest import FakeToolLLM

    p = FixtureProvider()
    p.upsert_live([Movie(id="imdb-tt0057687", title="Apache Gold", title_de="Winnetou 1. Teil", year=1963)])
    service = SearchService(p)
    agent = FakeToolLLM(messages=iter([ai(calls=[("find_title", {"title": "Winnetou"})]), ai("Done.")]))
    explain = FakeToolLLM(messages=iter([AIMessage("**Winnetou 1. Teil** (1963) — the first part of the trilogy.")]))
    g = build_graph(agent, explain, make_tools(ToolKit(service, p, None)), service, p, MemorySaver())
    out = run_turn(g, "t-de", "Winnetou", empty())
    assert "German title: Winnetou 1. Teil" in out["prompts"]["explain_input"]
    assert not out.get("grounding_fallback") and "Winnetou 1. Teil" in out["reply"]
