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

    def semantic_search(self, query_embedding, k: int = 20):
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
