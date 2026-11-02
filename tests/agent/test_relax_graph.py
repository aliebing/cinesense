from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver

from cinesense.agent.graph import build_graph, run_turn
from cinesense.agent.tools import ToolKit, make_tools
from cinesense.domain.criteria import SearchCriteria
from cinesense.providers.fixture import FixtureProvider
from cinesense.search.service import SearchService

from .conftest import FakeToolLLM, ai

# Fixture facts: only Toy Story (80) and Shrek (90) run <= 90 min, so a 60-min limit finds nothing and the
# runtime option (90 min) finds 2 — still < 3, which leads to a second round. Scripts end with spare messages.
HMM = [ai("Hmm.")] * 3


def crit(**kw):
    return SearchCriteria(**kw).model_dump()


def test_agent_picks_relaxation(make_agent):
    g = make_agent(
        [
            ai(
                calls=[
                    ("set_mood_tags", {"tags": [{"name": "funny", "mode": "must"}]}),
                    ("set_filters", {"max_runtime_min": 60}),
                ]
            ),
            ai("Done."),
            ai(calls=[("relax_search", {"option_id": "runtime"})]),
            ai("Done."),
            *HMM,
        ]
    )
    out = run_turn(g, "r1", "something funny under an hour", crit())
    assert out["relaxed"][0] == "Allow up to 90 min"
    assert out["results"]


def test_auto_relax_when_model_does_not_pick(make_agent):
    g = make_agent([ai(calls=[("set_filters", {"max_runtime_min": 60})]), ai("Done."), *HMM])
    out = run_turn(g, "r2", "very short film", crit())
    assert out["relaxed"][0] == "Allow up to 90 min"
    assert out["results"]


def test_relaxation_keeps_no_horror(make_agent):
    g = make_agent(
        [
            ai(
                calls=[
                    ("set_mood_tags", {"tags": [{"name": "horror", "mode": "not"}]}),
                    ("set_filters", {"max_runtime_min": 60}),
                ]
            ),
            ai("Done."),
            *HMM,
        ]
    )
    out = run_turn(g, "r3", "no horror, very short", crit())
    assert out["relaxed"]
    assert "Horror" in out["criteria"]["exclude_genres"]
    assert not any("Horror" in r["movie"]["genres"] for r in out["results"])


def test_relaxation_is_bounded(make_agent):
    stubborn = [ai(calls=[("set_filters", {"max_runtime_min": 60})]), ai("Done.")] * 15
    g = make_agent(stubborn)
    out = run_turn(g, "r4", "short", crit())  # must return, not hit the recursion limit
    assert out["reply"] and len(out["relaxed"]) <= 2


def test_enough_results_means_no_relaxation(make_agent):
    g = make_agent([ai(calls=[("set_mood_tags", {"tags": [{"name": "space travel"}]})]), ai("Done.")])
    out = run_turn(g, "r5", "space", crit())
    assert out["relaxed"] == []


def test_verify_survives_probe_errors(make_agent, monkeypatch):
    def boom(self, c):
        raise RuntimeError("db down")

    monkeypatch.setattr(SearchService, "count", boom)
    g = make_agent([ai(calls=[("set_filters", {"max_runtime_min": 60})]), ai("Done.")])
    out = run_turn(g, "r6", "short", crit())
    assert out["reply"] and out["relaxed"] == []


class CinemaProvider(FixtureProvider):
    """Groundhog Day is in cinemas, has no Tag Genome vector, and is the plot search's hit."""

    def __init__(self):
        super().__init__()
        m = self._by_id["ml-1265"]
        m.availability.in_cinema_de = True
        self._vectors.pop("ml-1265")

    def semantic_search(self, query_embedding, k: int = 20, only_ids=None):
        return [(self._by_id["ml-1265"], 0.8, "A weatherman relives the same day.")]


class Embedder:
    async def embed(self, texts):
        return [[0.1] * 4 for _ in texts]


def test_cinema_tags_fall_back_to_plot_search():
    p = CinemaProvider()
    service = SearchService(p, embedder=Embedder())
    script = [
        ai(calls=[("set_mood_tags", {"tags": [{"name": "funny"}]}), ("set_filters", {"availability": "cinema"})]),
        ai("Done."),
        ai(calls=[("relax_search", {"option_id": "tags-to-plot"})]),
        ai("Done."),
        *HMM,
    ]
    g = build_graph(
        FakeToolLLM(messages=iter(script)),
        FakeToolLLM(messages=iter([AIMessage("Here.")])),
        make_tools(ToolKit(service, p, None)),
        service,
        p,
        MemorySaver(),
    )
    out = run_turn(g, "r7", "something funny in cinemas", crit())
    assert [r["movie"]["id"] for r in out["results"]] == ["ml-1265"]
    assert out["criteria"]["availability"] == "cinema"
    assert out["relaxed"] == ["Search the mood (funny) in plot descriptions"]


def test_relaxed_labels_do_not_trip_grounding(make_agent):
    # 90 min finds only 2 films, so the search is widened twice
    reply = "Nothing matched every wish, so I widened the search: **Allow up to 90 min**, then **Allow up to 120 min**."
    g = make_agent([ai(calls=[("set_filters", {"max_runtime_min": 60})]), ai("Done."), *HMM], [AIMessage(reply)])
    out = run_turn(g, "r8", "very short film", crit())
    assert out["relaxed"] == ["Allow up to 90 min", "Allow up to 120 min"]
    assert out["grounding_fallback"] is False, out["grounding_reason"]
    assert out["reply"] == reply


def test_explain_input_names_the_widening(make_agent):
    g = make_agent([ai(calls=[("set_filters", {"max_runtime_min": 60})]), ai("Done."), *HMM])
    out = run_turn(g, "r9", "very short film", crit())
    assert "Widened: Allow up to 90 min" in out["prompts"]["explain_input"]


def test_widened_results_carry_misses(make_agent):
    g = make_agent([ai(calls=[("set_filters", {"max_runtime_min": 60})]), ai("Done."), *HMM])
    out = run_turn(g, "r10", "very short film", crit())
    assert out["results"]
    for r in out["results"]:
        assert r["misses"] == [f"{r['movie']['runtime_min']} min, longer than 60"]


def test_unwidened_results_have_no_misses(make_agent):
    g = make_agent([ai(calls=[("set_mood_tags", {"tags": [{"name": "space travel"}]})]), ai("Done.")])
    out = run_turn(g, "r11", "space", crit())
    assert out["results"] and all(r["misses"] == [] for r in out["results"])


def test_original_criteria_reset_each_turn(make_agent):
    first = [ai(calls=[("set_filters", {"max_runtime_min": 60})]), ai("Done."), ai("Hmm."), ai("Hmm.")]
    second = [ai(calls=[("set_filters", {"max_runtime_min": 150})]), ai("Done.")]
    g = make_agent(first + second, [AIMessage("A."), AIMessage("B.")])
    assert run_turn(g, "r12", "very short film", crit())["relaxed"]
    out = run_turn(g, "r12", "up to 150 minutes", crit(max_runtime_min=120))
    assert out["relaxed"] == []
    assert out["results"] and all(r["misses"] == [] for r in out["results"])


SEEN: list = []


class RecordingLLM(FakeToolLLM):
    """Like the real provider: a request may not end with an assistant message (Anthropic rejects it with 400)."""

    def invoke(self, input, config=None, **kwargs):
        SEEN.append(list(input))
        return super().invoke(input, config, **kwargs)


def test_relax_offer_never_ends_the_request_with_an_assistant_message():
    from langchain_core.messages import HumanMessage

    SEEN.clear()
    p = FixtureProvider()
    service = SearchService(p)
    script = [ai(calls=[("set_filters", {"max_runtime_min": 60})]), ai("Done."), *HMM]
    g = build_graph(
        RecordingLLM(messages=iter(script)),
        FakeToolLLM(messages=iter([AIMessage("Here.")])),
        make_tools(ToolKit(service, p, None)),
        service,
        p,
        MemorySaver(),
    )
    out = run_turn(g, "r13", "very short film", crit())
    assert out["relaxed"]
    offers = [m for m in SEEN if "Ways to widen it" in str(m[-1].content)]
    assert offers and all(isinstance(m[-1], HumanMessage) for m in offers)
    assert all(not isinstance(m[-1], AIMessage) for m in SEEN)
    # the note is sent, not stored: the next turn's history has no such user message
    history = g.get_state({"configurable": {"thread_id": "r13"}}).values["messages"]
    assert not any("Ways to widen it" in str(m.content) for m in history)


def test_after_a_relaxation_the_search_runs_before_the_model_can_undo_it(make_agent):
    g = make_agent(
        [
            ai(calls=[("set_filters", {"max_runtime_min": 60})]),
            ai("Done."),
            ai(calls=[("relax_search", {"option_id": "runtime"})]),  # 90 min: 2 films, offered again
            ai(calls=[("set_filters", {"max_runtime_min": 60})]),  # tries to undo the widening
            ai("Done."),
            *HMM,
        ]
    )
    out = run_turn(g, "r14", "very short film", crit())
    assert out["relaxed"] == ["Allow up to 90 min", "Allow up to 120 min"]
    assert out["criteria"]["max_runtime_min"] == 120


def test_other_tools_wait_while_a_relaxation_is_offered(make_agent):
    g = make_agent(
        [
            ai(calls=[("set_filters", {"max_runtime_min": 60})]),
            ai("Done."),
            ai(calls=[("set_filters", {"year_from": 2020})]),  # ignores the offer
            *HMM,
        ]
    )
    out = run_turn(g, "r15", "very short film", crit())
    assert out["criteria"]["year_from"] is None
    assert out["relaxed"]
