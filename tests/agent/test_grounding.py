from langchain_core.messages import AIMessage

from cinesense.agent.graph import run_turn
from cinesense.agent.grounding import template_answer, validate_titles
from cinesense.domain.criteria import SearchCriteria

from .conftest import ai

CATALOGUE = {"Titanic", "The Matrix", "Up", "Fight Club", "The Shawshank Redemption"}


def test_flags_unlisted_title():
    ok, bad = validate_titles("Try **Titanic** or The Shawshank Redemption.", ["The Matrix"], CATALOGUE)
    assert not ok and set(bad) == {"Titanic", "The Shawshank Redemption"}


def test_accepts_listed_titles_and_common_words():
    ok, bad = validate_titles("**The Matrix** is great, and it will cheer you up.", ["The Matrix"], CATALOGUE)
    assert ok and bad == []


def test_template_answer_lists_results():
    text = template_answer([{"movie": {"title": "The Matrix", "year": 1999}, "reasons": ["dark 91%"]}])
    assert "**The Matrix** (1999)" in text and "dark 91%" in text


def test_fallback_used_when_invalid(make_agent):
    g = make_agent(
        [ai(calls=[("set_mood_tags", {"tags": [{"name": "dark"}]})]), ai("ok")],
        explain_msgs=[ai("You will love **Not In Results Movie Title** and **Titanic**.")],
    )
    out = run_turn(g, "g1", "dark films", SearchCriteria().model_dump())
    assert "Titanic" not in out["reply"] and out["grounding_fallback"]


def test_truncated_explanation_falls_back(make_agent):
    cut = AIMessage("These films share a", response_metadata={"finish_reason": "length"})
    g = make_agent([ai(calls=[("set_mood_tags", {"tags": [{"name": "dark"}]})]), ai("ok")], explain_msgs=[cut])
    out = run_turn(g, "g2", "dark films", SearchCriteria().model_dump())
    assert out["grounding_fallback"] and out["reply"].startswith("Here are films")


TAGS = ["dark", "pulp", "time", "space", "love"]  # tags of the current search; never all 1,128
BIG = CATALOGUE | {"The Dark Knight", "Pulp Fiction", "Children of Men", "Alien", "Casino", "Creepy"}


def test_tag_words_never_hide_unlisted_titles():
    for reply in (
        "You might also enjoy The Dark Knight.",
        "Inception, and so is Pulp Fiction.",
        "Try **Alien** or **Casino**.",
    ):
        ok, _ = validate_titles(reply, ["Inception"], BIG, tag_spans=TAGS)
        assert not ok, reply


def test_emphasised_tag_from_the_criteria_is_not_a_film():
    assert validate_titles("Shall I also exclude **Creepy**?", [], BIG, tag_spans=["creepy"])[0]


def test_short_allowed_title_does_not_cut_words():
    ok, bad = validate_titles("**Up** is lovely, unlike The Dark Knight.", ["Up"], BIG)
    assert not ok and bad == ["The Dark Knight"]


def test_single_word_title_named_by_the_user_is_allowed():
    from cinesense.agent.grounding import user_named_titles

    cat = BIG | {"Mother", "Heat"}
    named = user_named_titles("Tell me more about the movie Alien", cat)
    assert named == ["Alien"]
    reply = '**Alien** (1979): the computer, "Mother", wakes the crew.'
    assert validate_titles(reply, named, cat)[0]
    assert not validate_titles("Also watch **Heat**.", named, cat)[0]


def test_pick_count_shows_three_to_five_close_matches():
    from cinesense.agent.grounding import pick_count

    def rs(*pcts):
        return [{"movie": {"title": f"F{i}"}, "match_percent": p} for i, p in enumerate(pcts)]

    assert pick_count(rs(94, 92, 92, 90, 90)) == 3  # the 4th is 4 points behind the best
    assert pick_count(rs(91, 90, 90, 90, 89, 89)) == 5  # all close: at most five
    assert pick_count(rs(93, 93, 90, 89)) == 3
    assert pick_count(rs(95, 94, 92, 92, 91)) == 4
    assert pick_count(rs(90, 60)) == 2  # fewer results than three
    assert pick_count([]) == 0


def test_template_answer_lists_the_close_matches():
    rs = [{"movie": {"title": f"Film {i}", "year": 2000}, "reasons": [], "match_percent": 90} for i in range(8)]
    assert template_answer(rs).count("**") == 2 * 5
