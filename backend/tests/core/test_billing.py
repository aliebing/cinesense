from cinesense.core.billing import billing_order, role_weight

PI = (
    "Life of Pi is a 2012 adventure drama film directed by Ang Lee. The film stars Suraj Sharma, Irrfan Khan, "
    "Rafe Spall, Tabu, Adil Hussain, and Gérard Depardieu."
)


def test_billing_follows_the_lead_not_the_wikidata_order():
    cast = ["Tabu", "Gérard Depardieu", "Suraj Sharma", "Irrfan Khan", "Élisabeth Depardieu"]
    order = billing_order(PI, cast)
    assert order["Suraj Sharma"] == 1 and order["Irrfan Khan"] == 2 and order["Tabu"] == 3
    assert order["Gérard Depardieu"] == 4
    assert order["Élisabeth Depardieu"] == 0  # named nowhere; the shared surname belongs to Gérard


def test_billing_matches_a_unique_surname_and_ignores_accents():
    lead = "Cyrano de Bergerac is a 1990 French film starring Gerard Depardieu. Perez plays Christian."
    order = billing_order(lead, ["Anne Brochet", "Gérard Depardieu", "Vincent Perez"])
    assert order == {"Gérard Depardieu": 1, "Vincent Perez": 2, "Anne Brochet": 0}


def test_billing_starts_at_the_cast_list_not_the_director_credit():
    lead = (
        "Pulp Fiction is a 1994 crime film written and directed by Quentin Tarantino. It stars John Travolta, "
        "Samuel L. Jackson and Uma Thurman."
    )
    order = billing_order(lead, ["Uma Thurman", "Quentin Tarantino", "John Travolta", "Samuel L. Jackson"])
    assert order == {"John Travolta": 1, "Samuel L. Jackson": 2, "Uma Thurman": 3, "Quentin Tarantino": 0}


def test_lead_without_any_cast_names_tells_nothing():
    assert billing_order("Hamlet is a 1996 film adapted from Shakespeare's play.", ["Billy Crystal"]) == {}


def test_role_weight_prefers_leads_over_cameos():
    lead, third, fifth, cameo, unknown = (role_weight("cast", b) for b in (1, 3, 5, 0, None))
    assert lead == role_weight("director", None) == 1.0
    assert lead > third > fifth > cameo
    assert cameo < unknown < lead


def test_a_lead_outranks_a_far_more_popular_cameo(tmp_path):
    """The Depardieu case: Life of Pi (huge, a small part) must not top Cyrano (his lead)."""
    import json

    from cinesense.core.criteria import SearchCriteria
    from cinesense.data_sources.fixture import FixtureProvider
    from cinesense.search.service import SearchService

    def film(id_, title, year, count, billing):
        return {
            "id": id_, "title": title, "year": year, "genres": ["Drama"], "world_ids": ["drama"],
            "ml_rating": 3.9, "ml_rating_count": count,
            "people": [{"name": "Gérard Depardieu", "role": "cast", "billing": billing}],
        }  # fmt: skip

    path = tmp_path / "films.json"
    path.write_text(json.dumps([film("pi", "Life of Pi", 2012, 60000, 6), film("cy", "Cyrano", 1990, 4000, 1)]))
    items = SearchService(FixtureProvider(path)).run(SearchCriteria(person="Gerard Depardieu"), 0, 5).items
    assert [r.movie.id for r in items] == ["cy", "pi"]


def test_top_cast_puts_the_lead_billing_first_then_the_rest_in_their_order():
    from cinesense.core.billing import top_cast

    names = ["Rick Ducommun", "Tracy Reiner", "Paul Gleason", "Alan Rickman", "Bruce Willis", "Bonnie Bedelia"]
    order = {"Bruce Willis": 1, "Alan Rickman": 2, "Bonnie Bedelia": 4, "Paul Gleason": 7}
    assert top_cast(names, order) == ["Bruce Willis", "Alan Rickman", "Bonnie Bedelia", "Paul Gleason", "Rick Ducommun"]
    assert top_cast(names, {}) == names[:5]  # no lead found: Wikidata's order
