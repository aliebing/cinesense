from datetime import date

import httpx
import respx

from cinesense.data_sources.wikidata import SPARQL_URL, fetch_wikidata, fold_bindings


def b(**kw):
    return {k: {"value": v} for k, v in kw.items()}


ROWS = [
    b(
        ml="109487",
        film="http://www.wikidata.org/entity/Q13417189",
        imdb="tt0816692",
        yt="x3jSPGsLc0Y",
        deDate="2014-11-06T00:00:00Z",
        runtime="169",
        lang="en",
        enwiki="https://en.wikipedia.org/wiki/Interstellar_(film)",
        director="Christopher Nolan",
        cast="Matthew McConaughey",
        castOrd="1",
    ),
    b(
        ml="109487",
        film="http://www.wikidata.org/entity/Q13417189",
        imdb="tt0816692",
        yt="F6TU69adAzE",
        deDate="2014-11-07T00:00:00Z",
        runtime="169",
        lang="en",
        enwiki="https://en.wikipedia.org/wiki/Interstellar_(film)",
        director="Christopher Nolan",
        cast="Matthew McConaughey",
        castOrd="1",
    ),
    b(
        ml="109487",
        film="http://www.wikidata.org/entity/Q13417189",
        imdb="tt0816692",
        director="Christopher Nolan",
        cast="Anne Hathaway",
        castOrd="2",
    ),
]


def test_fold_rows_picks_earliest_de_date_first_trailer_and_dedupes():
    films = fold_bindings(ROWS)
    f = films[109487]
    assert f.wikidata_id == "Q13417189"
    assert f.imdb_id == "tt0816692"
    assert f.release_date_de == date(2014, 11, 6)
    assert f.youtube_key == "F6TU69adAzE"  # lexicographically first, deterministic
    assert f.runtime_min == 169 and f.original_language == "en"
    assert f.wikipedia_title == "Interstellar (film)"
    assert f.directors == ["Christopher Nolan"]
    assert f.cast == ["Matthew McConaughey", "Anne Hathaway"]


@respx.mock
async def test_fetch_wikidata_batches():
    route = respx.post(SPARQL_URL).mock(return_value=httpx.Response(200, json={"results": {"bindings": ROWS}}))
    async with httpx.AsyncClient() as client:
        out = await fetch_wikidata(list(range(1, 302)), client, batch=150)
    assert route.call_count == 6  # 3 batches x (scalars + people)
    assert 109487 in out


@respx.mock
async def test_fetch_by_imdb_gives_the_german_title_and_the_wikipedia_article():
    from cinesense.data_sources.wikidata import fetch_by_imdb

    rows = [
        b(
            imdb="tt0057687",
            film="http://www.wikidata.org/entity/Q571904",
            deLabel="Winnetou 1. Teil",
            enwiki="https://en.wikipedia.org/wiki/Apache_Gold",
            yt="abc123",
            lang="de",
        )
    ]
    route = respx.post(SPARQL_URL).mock(return_value=httpx.Response(200, json={"results": {"bindings": rows}}))
    async with httpx.AsyncClient() as client:
        out = await fetch_by_imdb(["tt0057687"], client)
    assert route.call_count == 1
    f = out["tt0057687"]
    assert (f.wikidata_id, f.title_de, f.wikipedia_title) == ("Q571904", "Winnetou 1. Teil", "Apache Gold")
    assert (f.youtube_key, f.original_language, f.imdb_id) == ("abc123", "de", "tt0057687")
    assert '"tt0057687"' in route.calls[0].request.content.decode().replace("%22", '"')


@respx.mock
async def test_fetch_german_titles_by_wikidata_id():
    from cinesense.data_sources.wikidata import fetch_german_titles

    rows = [b(film="http://www.wikidata.org/entity/Q1", deLabel="Der Schuh des Manitu")]
    route = respx.post(SPARQL_URL).mock(return_value=httpx.Response(200, json={"results": {"bindings": rows}}))
    async with httpx.AsyncClient() as client:
        out = await fetch_german_titles(["Q1", "Q2", "not-a-qid"], client)
    assert out == {"Q1": "Der Schuh des Manitu"} and route.call_count == 1
    assert (
        "wd%3AQ2" in route.calls[0].request.content.decode()
        and "not-a-qid" not in route.calls[0].request.content.decode()
    )


def test_fold_rows_choose_the_same_language_whatever_the_row_order():
    rows = [b(ml="1", film="http://www.wikidata.org/entity/Q1", lang=x) for x in ("it", "de")]
    assert fold_bindings(rows)[1].original_language == fold_bindings(rows[::-1])[1].original_language == "de"
