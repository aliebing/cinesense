"""Wikidata (CC0) enrichment by MovieLens id (P14449): ids, trailer, runtime, language, people, DE release.
Films imported live (no MovieLens id) are looked up by IMDb id (P345) instead: German title, Wikipedia article."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date
from urllib.parse import unquote

import httpx

log = logging.getLogger(__name__)

SPARQL_URL = "https://query.wikidata.org/sparql"
USER_AGENT = "CineSense-capstone/0.1 (https://github.com/aliebing; student project) httpx"
HEADERS = {"Accept": "application/sparql-results+json", "User-Agent": USER_AGENT}

_SCALARS = """
SELECT ?ml ?film ?imdb ?yt ?runtime ?lang ?deDate ?enwiki WHERE {
  VALUES ?ml { %s }
  ?film wdt:P14449 ?ml .
  OPTIONAL { ?film wdt:P345 ?imdb }
  OPTIONAL { ?film wdt:P1651 ?yt }
  OPTIONAL { ?film wdt:P2047 ?runtime }
  OPTIONAL { ?film wdt:P364 ?l . ?l wdt:P218 ?lang }
  OPTIONAL { ?film p:P577 ?st . ?st ps:P577 ?deDate ; pq:P291 wd:Q183 }
  OPTIONAL { ?enwiki schema:about ?film ; schema:isPartOf <https://en.wikipedia.org/> }
  OPTIONAL { ?film rdfs:label ?deLabel FILTER(LANG(?deLabel) = "de") }
}"""

_GERMAN = """
SELECT ?film ?deLabel WHERE {
  VALUES ?film { %s }
  ?film rdfs:label ?deLabel FILTER(LANG(?deLabel) = "de")
}"""

_BY_IMDB = """
SELECT ?imdb ?film ?deLabel ?yt ?lang ?enwiki WHERE {
  VALUES ?imdb { %s }
  ?film wdt:P345 ?imdb .
  OPTIONAL { ?film rdfs:label ?deLabel FILTER(LANG(?deLabel) = "de") }
  OPTIONAL { ?film wdt:P1651 ?yt }
  OPTIONAL { ?film wdt:P364 ?l . ?l wdt:P218 ?lang }
  OPTIONAL { ?enwiki schema:about ?film ; schema:isPartOf <https://en.wikipedia.org/> }
}"""


def name_of(item: str, var: str) -> str:
    """SPARQL for a person's name: the English label, else the multilingual 'mul' one. Wikidata moves names to
    'mul' and drops the identical English label (Bruce Willis has only 'mul'); English-only lost those people."""
    return (
        f'OPTIONAL {{ {item} rdfs:label ?{var}En FILTER(LANG(?{var}En) = "en") }} '
        f'OPTIONAL {{ {item} rdfs:label ?{var}Mul FILTER(LANG(?{var}Mul) = "mul") }} '
        f"BIND(COALESCE(?{var}En, ?{var}Mul) AS ?{var}) FILTER(BOUND(?{var}))"
    )


_PEOPLE_PATTERN = f"""
  {{ ?film wdt:P57 ?d . {name_of("?d", "director")} }}
  UNION
  {{ ?film p:P161 ?cs . ?cs ps:P161 ?c . {name_of("?c", "cast")}
    OPTIONAL {{ ?cs pq:P1545 ?castOrd }} }}"""

_PEOPLE = (
    """
SELECT ?ml ?film ?director ?cast ?castOrd WHERE {
  VALUES ?ml { %s }
  ?film wdt:P14449 ?ml ."""
    + _PEOPLE_PATTERN.replace("%", "%%")
    + "\n}"
)

# the same by Wikidata id: refreshing the people of films already in the catalogue
_PEOPLE_BY_QID = (
    """
SELECT ?film ?director ?cast ?castOrd WHERE {
  VALUES ?film { %s }"""
    + _PEOPLE_PATTERN.replace("%", "%%")
    + "\n}"
)


@dataclass
class WikidataFilm:
    movielens_id: int | None
    wikidata_id: str
    imdb_id: str | None = None
    youtube_key: str | None = None
    runtime_min: int | None = None
    original_language: str | None = None
    release_date_de: date | None = None
    wikipedia_title: str | None = None
    title: str | None = None
    title_de: str | None = None
    year: int | None = None
    directors: list[str] = field(default_factory=list)
    cast: list[str] = field(default_factory=list)


def _v(row: dict, key: str) -> str | None:
    return row[key]["value"] if key in row else None


def _qid(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def _wiki_title(url: str) -> str:
    return unquote(url.rsplit("/wiki/", 1)[-1]).replace("_", " ")


def _parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def fold_bindings(rows: list[dict], key: str = "ml") -> dict:
    """Fold SPARQL rows (one film may span many rows) into one WikidataFilm per key, deterministically."""
    films: dict = {}
    trailers: dict = {}
    cast_rows: dict = {}
    langs: dict = {}
    for row in rows:
        k = _v(row, key)
        if k is None:
            continue
        k = int(k) if key == "ml" else k
        f = films.get(k)
        if f is None:
            f = films[k] = WikidataFilm(movielens_id=k if key == "ml" else None, wikidata_id=_qid(_v(row, "film")))
        f.imdb_id = f.imdb_id or _v(row, "imdb")
        if (rt := _v(row, "runtime")) and f.runtime_min is None:
            try:
                f.runtime_min = round(float(rt))
            except ValueError:
                pass
        if lang := _v(row, "lang"):
            langs.setdefault(k, set()).add(lang)
        if (url := _v(row, "enwiki")) and not f.wikipedia_title:
            f.wikipedia_title = _wiki_title(url)
        if (d := _v(row, "deDate")) and (pd := _parse_date(d)):
            f.release_date_de = min(f.release_date_de, pd) if f.release_date_de else pd
        if yt := _v(row, "yt"):
            trailers.setdefault(k, set()).add(yt)
        f.imdb_id = f.imdb_id or (k if key == "imdb" else None)
        f.title_de = f.title_de or _v(row, "deLabel")
        if (t := _v(row, "filmLabel")) and not f.title:
            f.title = t
        if (y := _v(row, "year")) and f.year is None:
            f.year = int(y[:4])
        if (name := _v(row, "director")) and name not in f.directors:
            f.directors.append(name)
        if name := _v(row, "cast"):
            ordv = _v(row, "castOrd")
            order = int(ordv) if ordv and ordv.isdigit() else 10_000
            cast_rows.setdefault(k, {}).setdefault(name, order)
    for k, ids in trailers.items():
        films[k].youtube_key = sorted(ids)[0]
    for k, found in langs.items():  # a stable first guess; languages.fetch_languages settles ties
        films[k].original_language = sorted(found)[0]
    for k, names in cast_rows.items():
        # by explicit ordinal, then first-seen order (dicts keep insertion order)
        films[k].cast = [n for n, _ in sorted(names.items(), key=lambda kv: kv[1])]
    return films


async def _sparql(client: httpx.AsyncClient, query: str, retries: int = 4) -> list[dict]:
    for attempt in range(retries):
        try:
            r = await client.post(SPARQL_URL, data={"query": query}, headers=HEADERS, timeout=90)
        except httpx.TimeoutException:
            if attempt == retries - 1:
                raise
            await asyncio.sleep(2**attempt * 3)
            continue
        if r.status_code in (429, 500, 502, 503, 504):
            await asyncio.sleep(2**attempt * 3)
            continue
        r.raise_for_status()
        return r.json()["results"]["bindings"]
    r.raise_for_status()
    return []


async def fetch_wikidata(
    movielens_ids: list[int], client: httpx.AsyncClient, batch: int = 150
) -> dict[int, WikidataFilm]:
    out: dict[int, WikidataFilm] = {}
    sem = asyncio.Semaphore(3)

    async def one(chunk: list[int]) -> None:
        values = " ".join(f'"{i}"' for i in chunk)
        async with sem:
            rows = await _sparql(client, _SCALARS % values)
            rows += await _sparql(client, _PEOPLE % values)
        out.update(fold_bindings(rows))

    await asyncio.gather(*(one(movielens_ids[i : i + batch]) for i in range(0, len(movielens_ids), batch)))
    return out


async def fetch_people(qids: list[str], client: httpx.AsyncClient, batch: int = 50) -> dict[str, WikidataFilm]:
    """Directors and cast by Wikidata id (WikidataFilm keyed by QID, only `directors` and `cast` filled). A batch
    that keeps failing is left out (its films keep their people) instead of failing the whole run."""
    out: dict[str, WikidataFilm] = {}
    sem = asyncio.Semaphore(3)

    async def one(chunk: list[str]) -> None:
        async with sem:
            try:
                rows = await _sparql(client, _PEOPLE_BY_QID % " ".join(f"wd:{q}" for q in chunk))
            except httpx.HTTPError as e:
                log.warning("People: batch of %d films skipped (%s)", len(chunk), type(e).__name__)
                return
        for f in fold_bindings(rows, key="film").values():
            out[f.wikidata_id] = f

    await asyncio.gather(*(one(qids[i : i + batch]) for i in range(0, len(qids), batch)))
    return out


async def fetch_by_imdb(imdb_ids: list[str], client: httpx.AsyncClient, batch: int = 150) -> dict[str, WikidataFilm]:
    """Films imported live from the Streaming API carry only an IMDb id: find their Wikidata item, German title,
    English Wikipedia article (for the plot), official trailer and original language."""
    out: dict[str, WikidataFilm] = {}
    for i in range(0, len(imdb_ids), batch):
        values = " ".join(f'"{x}"' for x in imdb_ids[i : i + batch] if x.startswith("tt") and x[2:].isdigit())
        if values:
            out.update(fold_bindings(await _sparql(client, _BY_IMDB % values), key="imdb"))
    return out


async def fetch_german_titles(qids: list[str], client: httpx.AsyncClient, batch: int = 400) -> dict[str, str]:
    """German titles (rdfs:label @de) of catalogue films, so a German title finds the film ("Der Schuh des Manitu"
    is "Manitou's Shoe" in MovieLens)."""
    valid = [q for q in qids if q.startswith("Q") and q[1:].isdigit()]
    out: dict[str, str] = {}
    sem = asyncio.Semaphore(3)

    async def one(chunk: list[str]) -> None:
        async with sem:
            rows = await _sparql(client, _GERMAN % " ".join(f"wd:{q}" for q in chunk))
        for row in rows:
            out.setdefault(_qid(_v(row, "film")), _v(row, "deLabel"))

    await asyncio.gather(*(one(valid[i : i + batch]) for i in range(0, len(valid), batch)))
    return out
