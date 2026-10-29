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
