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
