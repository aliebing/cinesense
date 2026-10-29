from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from cinesense.domain.criteria import SearchCriteria, TagCriterion
from cinesense.eval.baselines import RANKERS, rank, ranking_metrics
from cinesense.eval.judge import judge
from cinesense.providers.fixture import FixtureProvider

P = FixtureProvider()


def idx(tag):
    return P.list_tags().index(tag)


def test_all_rankers_apply_the_same_hard_filters():
    c = SearchCriteria(tags=[TagCriterion(idx=idx("dark"), weight=8)], max_runtime_min=110, exclude_genres=["Horror"])
    for name in RANKERS:
        films = rank(name, P, c, 10)
        assert films, name
        assert all((m.runtime_min or 0) <= 110 and "Horror" not in m.genres for m in films), name


def test_bayesian_ignores_tags_but_cinesense_uses_them():
    c = SearchCriteria(tags=[TagCriterion(idx=idx("space travel"), weight=9)])
    plain = rank("bayesian", P, SearchCriteria(), 5)
    assert [m.id for m in rank("bayesian", P, c, 5)] == [m.id for m in plain]
    m = ranking_metrics(P, c, {n: rank(n, P, c, 10) for n in RANKERS})
    assert m["cinesense"]["tag_relevance"] > m["bayesian"]["tag_relevance"]
    assert set(m["cosine"]) == {"tag_relevance", "median_rating_count", "constraint_ok"}


def fake(text):
    return GenericFakeChatModel(messages=iter([AIMessage(text)]))


def test_judge_parses_json_score():
    out = judge(
        fake('Sure: {"score": 4, "reason": "fits the dark space mood"}'),
        "dark space",
        [{"title": "Moon", "year": 2009}],
    )
    assert out == {"score": 4, "reason": "fits the dark space mood"}


def test_judge_malformed_output_gives_none():
    assert judge(fake("I think it's great!"), "w", [{"title": "A", "year": None}])["score"] is None
    assert judge(fake('{"score": 9, "reason": "x"}'), "w", [{"title": "A", "year": None}])["score"] is None


def test_judge_empty_list_skips_the_call():
    assert judge(None, "w", []) == {"score": None, "reason": "no films"}
