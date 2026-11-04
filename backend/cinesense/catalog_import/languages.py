"""Original language of a film. Wikidata often lists several equally ranked languages (dubbed or partly spoken
ones: Life Is Beautiful is German, English and Italian there). Of several, the first language in the English
Wikipedia infobox wins (it names the primary one first), then an official language of the country of origin,
then the first alphabetically, so the choice is stable across runs."""

import asyncio

import httpx

from cinesense.data_sources.wikidata import _qid, _sparql, _v, _wiki_title
from cinesense.data_sources.wikipedia import fetch_infobox_language

_LANGS = """SELECT ?film ?lang WHERE { VALUES ?film { %s } ?film wdt:P364 ?l . ?l wdt:P218 ?lang }"""
_DETAILS = """SELECT ?film ?c ?enwiki WHERE { VALUES ?film { %s }
  { ?film wdt:P495 ?c } UNION { ?enwiki schema:about ?film ; schema:isPartOf <https://en.wikipedia.org/> } }"""
_OFFICIAL = """SELECT ?c ?lang WHERE { VALUES ?c { %s } ?c wdt:P37 ?l . ?l wdt:P218 ?lang }"""
_NAMES = """SELECT ?code ?name WHERE { VALUES ?code { %s } ?l wdt:P218 ?code ; rdfs:label ?name
  FILTER(LANG(?name) = "en") }"""


def pick_language(langs: set[str], country_langs: set[str], primary: str | None = None) -> str | None:
    """One original language: a single one as is; of several, the infobox's primary language, else an official
    language of a country of origin, else the first alphabetically."""
    if not langs:
        return None
    if primary in langs:
        return primary
    return sorted(langs & country_langs or langs)[0]


def _values(items, fmt: str) -> str:
    return " ".join(fmt.format(x) for x in items)


async def fetch_languages(qids: list[str], client: httpx.AsyncClient, batch: int = 150) -> dict[str, str]:
    """The original language of each Wikidata item (see the module docstring)."""
    valid = [q for q in qids if q.startswith("Q") and q[1:].isdigit()]
    langs: dict[str, set[str]] = {}
    countries: dict[str, set[str]] = {}
    articles: dict[str, str] = {}
    sem = asyncio.Semaphore(3)

    async def one(chunk: list[str]) -> None:
        async with sem:
            for r in await _sparql(client, _LANGS % _values(chunk, "wd:{}")):
                langs.setdefault(_qid(_v(r, "film")), set()).add(_v(r, "lang"))
            several = [q for q in chunk if len(langs.get(q, ())) > 1]  # only ties need more
            if several:
                for r in await _sparql(client, _DETAILS % _values(several, "wd:{}")):
                    film = _qid(_v(r, "film"))
                    if c := _v(r, "c"):
                        countries.setdefault(film, set()).add(_qid(c))
                    if url := _v(r, "enwiki"):
                        articles[film] = url

    await asyncio.gather(*(one(valid[i : i + batch]) for i in range(0, len(valid), batch)))

    places = sorted({c for cs in countries.values() for c in cs})
    official: dict[str, set[str]] = {}
    for i in range(0, len(places), batch):
        for r in await _sparql(client, _OFFICIAL % _values(places[i : i + batch], "wd:{}")):
            official.setdefault(_qid(_v(r, "c")), set()).add(_v(r, "lang"))

    codes = sorted({x for found in langs.values() if len(found) > 1 for x in found})
    by_name: dict[str, str] = {}
    for i in range(0, len(codes), batch):
        for r in await _sparql(client, _NAMES % _values(codes[i : i + batch], '"{}"')):
            by_name.setdefault(_v(r, "name").lower(), _v(r, "code"))

    primary: dict[str, str] = {}
    wiki_sem = asyncio.Semaphore(4)

    async def infobox(q: str, url: str) -> None:
        async with wiki_sem:
            name = await fetch_infobox_language(_wiki_title(url), client)
        if name and (code := by_name.get(name.lower())):
            primary[q] = code

    await asyncio.gather(*(infobox(q, url) for q, url in articles.items()))

    out = {}
    for q, found in langs.items():
        spoken = {lang for c in countries.get(q, ()) for lang in official.get(c, ())}
        out[q] = pick_language(found, spoken, primary.get(q))
    return out
