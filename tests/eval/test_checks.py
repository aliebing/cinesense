from cinesense.eval.checks import check_constraints, check_grounding, check_reply, check_tools
from cinesense.eval.scenarios import Expect, load_scenarios


def r(title="A", runtime=100, genres=("Drama",), kind="film", year=2001, people=(), subs=None, streaming=None):
    return {
        "movie": {
            "title": title,
            "runtime_min": runtime,
            "genres": list(genres),
            "kind": kind,
            "year": year,
            "directors": list(people),
            "cast_top": [],
            "availability": {"in_cinema_de": False, "streaming_de": streaming, "subscription_services": subs or []},
        },
        "reasons": [],
    }


def test_scenarios_load_and_cover_the_spec():
    s = load_scenarios()
    cats = {x.category for x in s}
    assert len(s) >= 30 and {"mood", "like_x", "runtime", "exclusion", "conflict", "follow_up", "failure"} <= cats
    assert len({x.id for x in s}) == len(s)


def test_empty_results_fail_when_required():
    ok, why = check_constraints([], Expect())
    assert not ok and "no results" in why[0]
    assert check_constraints([], Expect(results_required=False))[0]


def test_constraint_violations_are_listed():
    results = [r("Long", runtime=150), r("Scary", genres=["Horror"]), r("Old", year=1980)]
    ok, why = check_constraints(results, Expect(max_runtime=120, exclude_genres=["Horror"], year_from=2000))
    assert not ok and any("Long" in w for w in why) and any("Scary" in w for w in why) and any("Old" in w for w in why)


def test_unknown_runtime_and_unknown_streaming_do_not_fail():
    ok, _ = check_constraints([r(runtime=None, streaming=None)], Expect(max_runtime=90, availability="stream"))
    assert ok
    assert not check_constraints([r(streaming=[], subs=[])], Expect(availability="stream"))[0]


def test_person_and_kind():
    assert check_constraints([r(people=["Christopher Nolan"])], Expect(person="Christopher Nolan"))[0]
    assert not check_constraints([r(people=["Someone"])], Expect(person="Christopher Nolan"))[0]
    assert not check_constraints([r(kind="film")], Expect(kind="documentary"))[0]


def test_tools_any_and_none():
    assert check_tools(["set_mood_tags", "set_filters"], Expect(tools_any=["set_filters"]))[0]
    assert not check_tools(["film_facts"], Expect(tools_any=["set_filters"]))[0]
    assert not check_tools(["check_streaming"], Expect(tools_none=["check_streaming"]))[0]
    assert check_tools([], Expect())[0]


def test_grounding_uses_the_validator():
    catalogue = {"Titanic", "The Matrix"}
    assert check_grounding("**The Matrix** fits.", [r("The Matrix")], catalogue, "")[0]
    assert not check_grounding("Try **Titanic**.", [r("The Matrix")], catalogue, "")[0]
    assert check_grounding("Titanic is from 1997.", [], catalogue, "Tell me about Titanic")[0]


def test_reply_contains_any_case_insensitive():
    assert check_reply("Directed by Ridley Scott in 1979.", Expect(reply_contains_any=["ridley scott"]))[0]
    assert not check_reply("", Expect(reply_contains_any=["1979"]))[0]
    assert check_reply("anything", Expect())[0]
