from datetime import date

import httpx
import respx

from cinesense.ingest.wikidata import SPARQL_URL, fetch_wikidata, fold_bindings


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
