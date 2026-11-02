import httpx
import respx

from cinesense.ingest.languages import fetch_languages, pick_language
from cinesense.ingest.wikidata import SPARQL_URL
from cinesense.ingest.wikipedia import API_URL, infobox_language

E = "http://www.wikidata.org/entity/"


def b(**kw):
    return {k: {"value": v} for k, v in kw.items()}


def test_pick_language_order_infobox_then_country_then_alphabet():
    assert pick_language({"de", "en", "it"}, set(), "it") == "it"  # Life Is Beautiful: Italian, not German
    assert pick_language({"en", "fr"}, {"en", "fr"}, "fr") == "fr"  # Café de Flore: Canada speaks both
    assert pick_language({"de", "en", "it"}, {"it"}) == "it"  # no infobox: the country of origin
    assert pick_language({"de", "en", "it"}, {"it"}, "ja") == "it"  # an infobox language not listed is no hint
    assert pick_language({"fr", "de"}, set()) == "de"  # nothing decides: stable alphabetical choice
    assert pick_language({"en"}, {"fr"}, "fr") == "en"  # a single language stays
    assert pick_language(set(), {"it"}) is None


def test_infobox_language_takes_the_first_one():
    assert (
        infobox_language("{{Infobox film\n| name = Lagaan\n| language = [[Hindi language|Hindi]]\n| budget = 1\n}}")
        == "Hindi"
    )
    plain = "{{Infobox film\n| language = {{Plainlist|\n* German\n* Polish\n* Yiddish\n}}\n| budget = 1\n}}"
    assert infobox_language(plain) == "German"
    note = "| language = Italian<!--Do not add German and English-->\n| budget = 1\n}}"
    assert infobox_language(note) == "Italian"
    assert infobox_language("| language = French<br>Catalan<br>Spanish\n| budget = 1") == "French"
    assert infobox_language("| language = {{ubl|German|English|French}}\n| budget = 1") == "German"
    assert infobox_language("{{Infobox film\n| name = X\n}}") is None


@respx.mock
async def test_fetch_languages_settles_ties_by_infobox_then_country():
    def sparql(request):
        q = request.content.decode()
        if "P364" in q:
            rows = [b(film=E + "Q1", lang=x) for x in ("de", "en", "it")] + [b(film=E + "Q2", lang="en")]
            rows += [b(film=E + "Q3", lang=x) for x in ("en", "fr")]
        elif "P495" in q:
            assert "Q2" not in q  # a film with one language needs nothing more
            rows = [b(film=E + "Q1", enwiki="https://en.wikipedia.org/wiki/Life_Is_Beautiful")]
            rows += [b(film=E + "Q3", c=E + "Q142")]
        elif "P37" in q:
            rows = [b(c=E + "Q142", lang="fr")]
        else:
            rows = [b(code=c, name=n) for c, n in (("de", "German"), ("en", "English"), ("it", "Italian"))]
        return httpx.Response(200, json={"results": {"bindings": rows}})

    respx.post(SPARQL_URL).mock(side_effect=sparql)
    page = {"revisions": [{"slots": {"main": {"content": "| language = [[Italian language|Italian]]\n| x = 1"}}}]}
    wiki = respx.get(API_URL).mock(return_value=httpx.Response(200, json={"query": {"pages": [page]}}))
    async with httpx.AsyncClient() as client:
        assert await fetch_languages(["Q1", "Q2", "Q3"], client) == {"Q1": "it", "Q2": "en", "Q3": "fr"}
    assert wiki.call_count == 1 and "Life+Is+Beautiful" in str(wiki.calls[0].request.url)
