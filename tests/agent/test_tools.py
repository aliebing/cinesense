import pytest

from cinesense.agent.tools import ToolKit
from cinesense.domain.criteria import SearchCriteria
from cinesense.providers.fixture import FixtureProvider
from cinesense.search.service import SearchService


class StubStreaming:
    def __init__(self):
        self.calls = 0

    def get_de(self, imdb_id):
        from cinesense.domain.models import StreamingOption

        self.calls += 1
        return [StreamingOption(service="Netflix", type="subscription")]


@pytest.fixture
def kit():
    p = FixtureProvider()
    return ToolKit(SearchService(p), p, StubStreaming())


def state(**kw):
    return {"criteria": SearchCriteria().model_dump(), "proposals": [], "streaming_checks": 0, **kw}


def test_set_mood_tags_merges_and_reports_unknown(kit):
    upd, msg = kit.set_mood_tags(state(), [{"name": "dark", "weight": 8}, {"name": "cozy vibes"}])
    tags = upd["criteria"]["tags"]
    assert len(tags) == 1 and tags[0]["weight"] == 8 and tags[0]["mode"] == "prefer"
    assert "cozy vibes" in msg and upd["criteria_changed"]
    upd2, _ = kit.set_mood_tags({**state(), "criteria": upd["criteria"]}, [{"name": "dark", "mode": "must"}])
    assert len(upd2["criteria"]["tags"]) == 1 and upd2["criteria"]["tags"][0]["mode"] == "must"


def test_nothing_scary_proposes_not_applies(kit):
    upd, _ = kit.set_mood_tags(state(), [{"name": "horror", "mode": "not"}])
    upd2, msg = kit.propose_exclusions({**state(), **upd}, ["scary", "creepy"])
    assert [t["mode"] for t in upd["criteria"]["tags"]] == ["not"]
    assert [p["tag"] for p in upd2["proposals"]] == ["scary", "creepy"]
    assert "criteria" not in upd2


def test_set_filters_and_clear(kit):
    upd, _ = kit.set_filters(state(), {"max_runtime_min": 110, "availability": "stream", "exclude_genres": ["Horror"]})
    c = upd["criteria"]
    assert c["max_runtime_min"] == 110 and c["availability"] == "stream" and c["exclude_genres"] == ["Horror"]
    upd2, _ = kit.set_filters({**state(), "criteria": c}, {"clear": ["max_runtime_min"]})
    assert upd2["criteria"]["max_runtime_min"] is None


def test_similar_to_uses_film_tags(kit):
    upd, msg = kit.similar_to(state(), "the matrix")
    assert "The Matrix" in msg
    assert len(upd["criteria"]["tags"]) == 5 and all(t["mode"] == "prefer" for t in upd["criteria"]["tags"])


def test_check_streaming_respects_per_turn_limit(kit):
    s = state()
    for _ in range(3):
        upd, msg = kit.check_streaming(s, "The Matrix")
        s = {**s, **upd}
    assert "Netflix" in msg
    upd, msg = kit.check_streaming(s, "The Matrix")
    assert "limit" in msg.lower() and kit.streaming.calls == 3


def test_show_on_stage_handoff(kit):
    upd, _ = kit.show_on_stage(state(), "The Matrix")
    assert upd["handoff"] == {"world_id": "suspense", "film_id": "ml-2571"}


def test_find_person_sets_criteria(kit):
    upd, msg = kit.find_person(state(), "Kianu Reeves")
    assert upd["criteria"]["person"] == "Keanu Reeves" and "Keanu Reeves" in msg


def test_not_horror_also_excludes_the_genre(kit):
    upd, _ = kit.set_mood_tags(state(), [{"name": "horror", "mode": "not"}])
    assert upd["criteria"]["exclude_genres"] == ["Horror"]


def test_not_horror_keeps_the_weight_it_reports(kit):
    upd, msg = kit.set_mood_tags(state(), [{"name": "horror", "mode": "not", "weight": 9}])
    assert [t["weight"] for t in upd["criteria"]["tags"]] == [9] and "horror (not, 9)" in msg


def test_find_person_without_matches_changes_nothing(kit):
    upd, msg = kit.find_person(state(), "Zzyzx Qwertyuiop")
    assert upd == {} and "not found" in msg.lower()


class StubLive:
    """Live title search: one film that is not in the catalogue."""

    def search_title(self, q):
        from cinesense.domain.models import Movie

        return [Movie(id="imdb-tt0057687", imdb_id="tt0057687", title="Apache Gold", year=1963, world_ids=["action"])]

    def search_person(self, q):
        return q, []


def test_find_title_finds_films_outside_the_catalogue_live():
    p = FixtureProvider()
    kit = ToolKit(SearchService(p, None, None, StubLive()), p, StubStreaming())
    upd, msg = kit.find_title(state(), "Winnetou")
    assert upd["criteria"]["title"] == "Winnetou"
    assert "Apache Gold (1963)" in msg
    assert p.get_movie("imdb-tt0057687") is not None  # imported, so the stage and film facts find it later


def test_find_title_without_matches_says_so(kit):
    upd, msg = kit.find_title(state(), "Zzyzx Qwertyuiop")
    assert upd == {} and "no film" in msg.lower()


def test_the_agent_gets_the_find_title_tool(kit):
    from cinesense.agent.tools import make_tools

    assert "find_title" in [t.name for t in make_tools(kit)]


def test_a_live_hit_never_lowers_a_better_catalogue_title_match():
    from cinesense.search.service import SearchService

    p = FixtureProvider()
    film = p.list_movies()[0]

    class EchoLive:
        def search_title(self, q):
            return [film]

    service = SearchService(p, None, None, EchoLive())
    from cinesense.search.service import Signals

    sig = Signals(title={film.id: 1.0})
    service._live(SearchCriteria(title=film.title), sig)
    assert sig.title[film.id] == 1.0


def test_the_search_reports_films_it_imported_live():
    p = FixtureProvider()
    imported = []
    service = SearchService(p, None, None, StubLive(), on_import=imported.extend)
    service.run(SearchCriteria(title="Winnetou"), 0, 5)
    assert imported == ["imdb-tt0057687"]
    service.run(SearchCriteria(title="Winnetou"), 0, 5)
    assert imported == ["imdb-tt0057687"]  # already in the catalogue: not reported again
