from cinesense.domain.criteria import SearchCriteria, TagCriterion
from cinesense.search.relax import Relaxation, apply, pick_auto, probe, relaxation_options

NAMES = {7: "funny", 9: "dark", 3: "horror"}
TAGS = [NAMES.get(i, f"t{i}") for i in range(1128)]


def ids(opts):
    return [o.id for o in opts]


def test_options_in_order():
    c = SearchCriteria(
        tags=[TagCriterion(idx=7, mode="must"), TagCriterion(idx=9)],
        max_runtime_min=90,
        year_from=2000,
        original_language="de",
        world_id="comedy",
        availability="cinema",
    )
    assert ids(relaxation_options(c, TAGS)) == [
        "must-to-prefer:7",
        "tags-to-plot",
        "runtime",
        "years",
        "language",
        "world",
        "availability",
    ]


def test_must_to_prefer_label_and_effect():
    c = SearchCriteria(tags=[TagCriterion(idx=7, mode="must", weight=8)])
    opt = relaxation_options(c, TAGS)[0]
    assert opt.label == "'funny' as a preference, not a must"
    assert [(t.idx, t.mode, t.weight) for t in opt.criteria.tags] == [(7, "prefer", 8)]
    assert c.tags[0].mode == "must"  # the input stays untouched


def test_tags_to_plot_keeps_not_tags_and_names_the_mood():
    c = SearchCriteria(tags=[TagCriterion(idx=7), TagCriterion(idx=9), TagCriterion(idx=3, mode="not")])
    opt = next(o for o in relaxation_options(c, TAGS) if o.id == "tags-to-plot")
    assert opt.criteria.plot_query == "funny, dark"
    assert [t.idx for t in opt.criteria.tags] == [3]
    assert opt.label == "Search the mood (funny, dark) in plot descriptions"


def test_no_tags_to_plot_when_a_plot_query_exists():
    c = SearchCriteria(tags=[TagCriterion(idx=7)], plot_query="heist")
    assert "tags-to-plot" not in ids(relaxation_options(c, TAGS))


def test_never_relaxes_exclusions_person_title_kind():
    c = SearchCriteria(
        tags=[TagCriterion(idx=3, mode="not")],
        exclude_genres=["Horror"],
        person="Keanu Reeves",
        title="Matrix",
        kind="documentary",
        max_runtime_min=90,
        availability="stream",
    )
    opts = relaxation_options(c, TAGS)
    assert opts
    for o in opts:
        assert o.criteria.exclude_genres == ["Horror"]
        assert any(t.idx == 3 and t.mode == "not" for t in o.criteria.tags)
        assert (o.criteria.person, o.criteria.title, o.criteria.kind) == ("Keanu Reeves", "Matrix", "documentary")


def test_runtime_years_availability_labels():
    opts = {o.id: o for o in relaxation_options(SearchCriteria(max_runtime_min=390, year_to=1999), TAGS)}
    assert opts["runtime"].criteria.max_runtime_min == 400 and opts["runtime"].label == "Allow up to 400 min"
    assert opts["years"].criteria.year_to == 2009 and opts["years"].label == "Widen the years to …–2009"
    both = {o.id: o for o in relaxation_options(SearchCriteria(year_from=1990, year_to=1999), TAGS)}
    assert both["years"].label == "Widen the years to 1980–2009"
    cin = {o.id: o for o in relaxation_options(SearchCriteria(availability="cinema"), TAGS)}
    stream = {o.id: o for o in relaxation_options(SearchCriteria(availability="stream"), TAGS)}
    assert cin["availability"].label == "Not only in cinemas" and cin["availability"].criteria.availability == "any"
    assert stream["availability"].label == "Not only streaming"


def test_simple_labels():
    c = SearchCriteria(original_language="de", world_id="comedy")
    assert [o.label for o in relaxation_options(c, TAGS)] == ["Any original language", "All mood worlds"]


def test_nothing_to_relax():
    assert relaxation_options(SearchCriteria(person="X", exclude_genres=["Horror"]), TAGS) == []


def test_probe_drops_options_that_do_not_help_and_survives_errors():
    class Service:
        def count(self, c):
            if c.availability == "any":
                raise RuntimeError("db down")
            if c.original_language is None:
                return 0
            return 1 if c.max_runtime_min == 120 else 4

    c = SearchCriteria(max_runtime_min=90, year_from=2000, original_language="de", availability="cinema")
    out = probe(Service(), c, TAGS, current=1)
    assert ids(out) == ["years"]  # runtime: 1 (no gain), language: 0, availability: raised
    assert out[0].count == 4


def test_pick_auto_prefers_order_then_count():
    a, b, c = (Relaxation(i, i, SearchCriteria(), n) for i, n in (("a", 2), ("b", 4), ("c", 9)))
    assert pick_auto([a, b, c]).id == "b"
    assert pick_auto([a]).id == "a"
    assert pick_auto([]) is None


def test_apply():
    assert apply(SearchCriteria(), "runtime", TAGS) is None
    assert apply(SearchCriteria(max_runtime_min=60), "runtime", TAGS).criteria.max_runtime_min == 90


def test_probe_skips_plot_search_when_embeddings_are_down():
    class Service:
        def can_embed(self, text):
            return False

        def count(self, c):
            return 10

    c = SearchCriteria(tags=[TagCriterion(idx=7)], availability="cinema")
    assert ids(probe(Service(), c, TAGS, current=0)) == ["availability"]
