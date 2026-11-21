import httpx
import respx

from cinesense.data_sources.film_lookup import WBSEARCH_URL, FilmLookup
from cinesense.data_sources.wikidata import SPARQL_URL
from cinesense.data_sources.wikipedia import API_URL


def row(qid, pub, **kw):
    r = {"film": {"value": f"http://www.wikidata.org/entity/{qid}"}, "pub": {"value": pub}}
    return {**r, **{k: {"value": v} for k, v in kw.items()}}


def search(*hits):
    return httpx.Response(200, json={"search": [{"id": q, "label": label} for q, label in hits]})


@respx.mock
def test_finds_the_film_of_that_year_with_its_wikipedia_plot():
    respx.get(WBSEARCH_URL).mock(return_value=search(("Q2", "Swept Away"), ("Q1", "Swept Away"), ("Q9", "Novel")))
    rows = [
        row("Q2", "2002-10-08T00:00:00Z", imdb="tt0291579"),
        row(
            "Q1",
            "1974-12-01T00:00:00Z",
            imdb="tt0073817",
            genreLabel="drama film",
            dirLabel="Lina Wertmüller",
            enwiki="https://en.wikipedia.org/wiki/Swept_Away_(1974_film)",
        ),
    ]  # Q9 is no film: the query only returns films
    respx.post(SPARQL_URL).mock(return_value=httpx.Response(200, json={"results": {"bindings": rows}}))
    text = "Swept Away is a 1974 film.\n\n== Plot ==\nA rich woman and a sailor are stranded.\n\n== Cast ==\nX"
    wiki = respx.get(API_URL).mock(
        return_value=httpx.Response(200, json={"query": {"pages": {"1": {"extract": text}}}})
    )
    film, plot = FilmLookup(httpx.Client()).find("Swept Away", 1974)
    assert film.id == "wd-Q1" and film.year == 1974 and film.imdb_id == "tt0073817"
    assert film.directors == ["Lina Wertmüller"] and film.genres == ["Drama"]
    assert film.wikipedia_title == "Swept Away (1974 film)"
    assert plot == "A rich woman and a sailor are stranded."
    assert wiki.calls.last.request.url.params["titles"] == "Swept Away (1974 film)"


@respx.mock
def test_without_a_plot_section_the_lead_is_used():
    respx.get(WBSEARCH_URL).mock(return_value=search(("Q5", "Small Film")))
    rows = [row("Q5", "2001-01-01T00:00:00Z", enwiki="https://en.wikipedia.org/wiki/Small_Film")]
    respx.post(SPARQL_URL).mock(return_value=httpx.Response(200, json={"results": {"bindings": rows}}))
    text = "Small Film is about a lighthouse keeper.\n\n== Reception ==\nGood."
    respx.get(API_URL).mock(return_value=httpx.Response(200, json={"query": {"pages": {"1": {"extract": text}}}}))
    _, plot = FilmLookup(httpx.Client()).find("Small Film")
    assert plot == "Small Film is about a lighthouse keeper."


@respx.mock
def test_an_invented_title_is_not_found():
    respx.get(WBSEARCH_URL).mock(return_value=search(("Q7", "Some Song")))
    respx.post(SPARQL_URL).mock(return_value=httpx.Response(200, json={"results": {"bindings": []}}))
    assert FilmLookup(httpx.Client()).find("Some Song") is None


@respx.mock
def test_a_failing_source_means_not_found():
    respx.get(WBSEARCH_URL).mock(return_value=httpx.Response(503))
    assert FilmLookup(httpx.Client()).find("Anything") is None
