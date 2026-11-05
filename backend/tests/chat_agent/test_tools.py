import pytest

from cinesense.chat_agent.tools import ToolKit
from cinesense.core.criteria import SearchCriteria
from cinesense.data_sources.fixture import FixtureProvider
from cinesense.search.service import SearchService


class StubStreaming:
    def __init__(self):
        self.calls = 0

    def get_de(self, imdb_id):
        from cinesense.core.models import StreamingOption

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
        from cinesense.core.models import Movie

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
    from cinesense.chat_agent.tools import make_tools

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


def test_relax_search_rejects_unoffered_option(kit):
    upd, msg = kit.relax_search({"criteria": SearchCriteria().model_dump(), "relax_options": []}, "runtime")
    assert upd == {} and "not available" in msg


def test_relax_search_applies_offered_option(kit):
    state = {
        "criteria": SearchCriteria(max_runtime_min=60).model_dump(),
        "relax_options": [{"id": "runtime", "label": "Allow up to 90 min", "count": 2}],
        "relaxed": [],
    }
    upd, msg = kit.relax_search(state, "runtime")
    assert upd["criteria"]["max_runtime_min"] == 90
    assert upd["relaxed"] == ["Allow up to 90 min"] and upd["relax_options"] == []
    assert upd["criteria_changed"] is True


def test_exclude_people_resolves_the_name_and_keeps_the_others(kit):
    s = state(criteria=SearchCriteria(exclude_people=["Tom Hanks"]).model_dump())
    upd, msg = kit.exclude_people(s, ["Kianu Reeves", "Zzyzx Qwertyuiop"])
    assert upd["criteria"]["exclude_people"] == ["Tom Hanks", "Keanu Reeves"]  # the found spelling, not the typo
    assert "Keanu Reeves" in msg and "Zzyzx Qwertyuiop" in msg and "not found" in msg.lower()


def test_exclude_people_replace_and_clear(kit):
    s = state(criteria=SearchCriteria(exclude_people=["Tom Hanks"]).model_dump())
    upd, _ = kit.exclude_people(s, [], replace=True)
    assert upd["criteria"]["exclude_people"] == []


def test_excluding_the_wanted_person_drops_them_as_wanted(kit):
    s = state(criteria=SearchCriteria(person="Keanu Reeves").model_dump())
    upd, _ = kit.exclude_people(s, ["Keanu Reeves"])
    assert upd["criteria"]["person"] is None and upd["criteria"]["exclude_people"] == ["Keanu Reeves"]


def test_new_search_clears_every_criterion(kit):
    from cinesense.chat_agent.tools import make_tools

    s = state(
        criteria=SearchCriteria(
            person="Sandra Bullock", exclude_people=["Sylvester Stallone"], year_from=2000, title="Speed"
        ).model_dump()
    )
    upd, msg = kit.new_search(s)
    assert upd["criteria"] == SearchCriteria().model_dump() and upd["criteria_changed"] is True
    assert "cleared" in msg.lower()
    assert "new_search" in [t.name for t in make_tools(kit)]


def test_set_filters_min_rating_and_clear(kit):
    upd, msg = kit.set_filters(state(), {"min_rating": 3.8})
    assert upd["criteria"]["min_rating"] == 3.8 and "min_rating" in msg
    upd2, _ = kit.set_filters({**state(), "criteria": upd["criteria"]}, {"clear": ["min_rating"]})
    assert upd2["criteria"]["min_rating"] is None
