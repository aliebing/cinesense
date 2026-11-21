from langchain_core.messages import AIMessage

from cinesense.chat_agent.identify import check_candidates, make_plot_judge
from cinesense.chat_agent.tools import ToolKit
from cinesense.core.criteria import SearchCriteria
from cinesense.core.models import Movie
from cinesense.data_sources.fixture import FixtureProvider
from cinesense.search.service import SearchService

ISLAND = Movie(id="wd-Q692592", wikidata_id="Q692592", imdb_id="tt0377309", title="Survival Island", year=2005)
WAVES = Movie(id="wd-Q1365", wikidata_id="Q1365", imdb_id="tt0073817", title="Swept Away", year=1974)
PLOTS = {"Survival Island": "A wife has an affair with a sailor on an island.", "Swept Away": "A rich woman."}


class StubLookup:
    def __init__(self):
        self.asked = []

    def find(self, title, year=None):
        self.asked.append((title, year))
        film = {"Survival Island": ISLAND, "Swept Away": WAVES}.get(title)
        return (film, PLOTS[title]) if film else None


def affair_judge(description, plot):
    return "affair" in plot


def state():
    return {"criteria": SearchCriteria(tags=[], person="Someone").model_dump()}


def test_each_guess_is_checked_by_its_real_plot():
    checked = check_candidates(
        "wife cheats on an island",
        [("Swept Away", 1974), ("Made Up", None), ("Survival Island", 2005)],
        StubLookup(),
        affair_judge,
    )
    assert [(c[0], c[4]) for c in checked] == [
        ("Swept Away", "no match"),
        ("Made Up", "not found"),
        ("Survival Island", "match"),
    ]


def test_identify_film_shows_every_confirmed_film_and_imports_it():
    p = FixtureProvider()
    imported = []
    kit = ToolKit(SearchService(p, on_import=imported.extend), p, None, StubLookup(), lambda d, plot: "a" in plot)
    upd, msg = kit.identify_film(
        state(),
        "wife cheats on an island",
        [{"title": "Survival Island", "year": 2005}, {"title": "Made Up"}, {"title": "Swept Away"}],
    )
    c = upd["criteria"]
    assert c["film_ids"] == ["wd-Q692592", "wd-Q1365"] and c["person"] is None and c["title"] is None
    assert "Survival Island (2005)" in msg and "Swept Away (1974)" in msg and "Made Up" not in msg
    assert imported == ["wd-Q692592", "wd-Q1365"]
    hits = SearchService(p).run(SearchCriteria(**c), 0, 5).items
    assert [h.movie.id for h in hits] == ["wd-Q692592", "wd-Q1365"]  # the model's most likely first
    assert "its Wikipedia plot matches your description" in hits[0].reasons


def test_a_rejected_guess_is_not_shown():
    p = FixtureProvider()
    kit = ToolKit(SearchService(p), p, None, StubLookup(), affair_judge)
    upd, msg = kit.identify_film(state(), "x", [{"title": "Swept Away"}, {"title": "Survival Island"}])
    assert upd["criteria"]["film_ids"] == ["wd-Q692592"] and "Swept Away" not in msg


def test_identify_film_uses_the_catalogues_own_copy():
    p = FixtureProvider()
    own = p.list_movies()[0]
    twin = ISLAND.model_copy(update={"imdb_id": own.imdb_id, "title": own.title, "year": own.year})

    class Twin:
        def find(self, title, year=None):
            return twin, "an affair"

    kit = ToolKit(SearchService(p), p, None, Twin(), affair_judge)
    upd, msg = kit.identify_film(state(), "x", [{"title": own.title}])
    assert upd["criteria"]["film_ids"] == [own.id] and p.get_movie(twin.id) is None


def test_identify_film_without_a_confirmed_guess_changes_nothing():
    p = FixtureProvider()
    kit = ToolKit(SearchService(p), p, None, StubLookup(), lambda d, plot: False)
    upd, msg = kit.identify_film(state(), "x", [{"title": "Swept Away"}, {"title": "Made Up"}])
    assert upd == {} and "search_plot" in msg


def test_identify_film_without_sources_falls_back():
    p = FixtureProvider()
    upd, msg = ToolKit(SearchService(p), p, None).identify_film(state(), "x", [{"title": "A"}])
    assert upd == {} and "search_plot" in msg


class FakeLLM:
    def __init__(self, answer):
        self.answer = answer
        self.seen = None

    def invoke(self, messages):
        self.seen = messages
        if isinstance(self.answer, Exception):
            raise self.answer
        return AIMessage(self.answer)


def test_the_judge_sees_only_the_sources_plot_and_answers_yes_or_no():
    llm = FakeLLM("Yes.")
    assert make_plot_judge(llm)("a wife cheats", "The real plot.") is True
    assert "The real plot." in llm.seen[1].content and "a wife cheats" in llm.seen[1].content
    assert make_plot_judge(FakeLLM("no"))("a", "b") is False


def test_the_judge_never_confirms_without_a_plot_or_on_errors():
    assert make_plot_judge(FakeLLM("yes"))("a", "  ") is False
    assert make_plot_judge(FakeLLM(RuntimeError("down")))("a", "plot") is False
