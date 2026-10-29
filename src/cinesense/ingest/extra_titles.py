"""Titles beyond the Tag Genome: German releases since 2021 straight from Wikidata (no mood tags)."""

from datetime import date

import httpx

from cinesense.ingest.wikidata import _parse_date, _qid, _sparql, _v, _wiki_title
from cinesense.ingest.worlds_map import assign_worlds, normalise_wikidata_genres

DOCUMENTARY = "Q93204"

_RECENT = """
SELECT ?film ?filmLabel ?type ?deDate ?pub ?imdb ?yt ?runtime ?lang ?enwiki WHERE {
  ?film p:P577 ?st . ?st ps:P577 ?deDate ; pq:P291 wd:Q183 .
  FILTER(?deDate >= "%s"^^xsd:dateTime)
  VALUES ?type { wd:Q11424 wd:Q93204 }
  ?film wdt:P31 ?type .
  ?enwiki schema:about ?film ; schema:isPartOf <https://en.wikipedia.org/> .
  OPTIONAL { ?film wdt:P577 ?pub }
  OPTIONAL { ?film wdt:P345 ?imdb }
  OPTIONAL { ?film wdt:P1651 ?yt }
  OPTIONAL { ?film wdt:P2047 ?runtime }
  OPTIONAL { ?film wdt:P364 ?l . ?l wdt:P218 ?lang }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}"""

_DETAILS = """
SELECT ?film ?director ?cast ?castOrd ?genreLabel WHERE {
  VALUES ?film { %s }
  { ?film wdt:P57 ?d . ?d rdfs:label ?director FILTER(LANG(?director) = "en") }
  UNION
  { ?film p:P161 ?cs . ?cs ps:P161 ?c . ?c rdfs:label ?cast FILTER(LANG(?cast) = "en")
    OPTIONAL { ?cs pq:P1545 ?castOrd } }
  UNION
  { ?film wdt:P136 ?g . ?g rdfs:label ?genreLabel FILTER(LANG(?genreLabel) = "en") }
}"""


def fold_recent(rows: list[dict]) -> list[dict]:
    """Fold SPARQL rows into film rows (same shape as pipeline.film_row) keyed by 'wd-<QID>'."""
    films: dict[str, dict] = {}
    for row in rows:
        qid = _qid(_v(row, "film"))
        f = films.setdefault(
            qid,
            {
                "id": f"wd-{qid}",
                "movielens_id": None,
                "wikidata_id": qid,
                "imdb_id": None,
                "kind": "film",
                "title": None,
                "year": None,
                "runtime_min": None,
                "original_language": None,
                "genres": [],
                "directors": [],
                "cast": [],
                "youtube_ids": set(),
                "release_date_de": None,
                "wikipedia_title": None,
                "ml_rating": None,
                "ml_rating_count": 0,
                "tag_vector": None,
            },
        )
        f["title"] = f["title"] or _v(row, "filmLabel")
        if (t := _v(row, "type")) and _qid(t) == DOCUMENTARY:
            f["kind"] = "documentary"
        if (d := _v(row, "deDate")) and (pd := _parse_date(d)):
            f["release_date_de"] = min(f["release_date_de"], pd) if f["release_date_de"] else pd
        if (p := _v(row, "pub")) and (pp := _parse_date(p)):
            f["year"] = min(f["year"], pp.year) if f["year"] else pp.year
        f["imdb_id"] = f["imdb_id"] or _v(row, "imdb")
        if yt := _v(row, "yt"):
            f["youtube_ids"].add(yt)
        if (rt := _v(row, "runtime")) and f["runtime_min"] is None:
            try:
                f["runtime_min"] = round(float(rt))
            except ValueError:
                pass
        f["original_language"] = f["original_language"] or _v(row, "lang")
        if (url := _v(row, "enwiki")) and not f["wikipedia_title"]:
            f["wikipedia_title"] = _wiki_title(url)
        if (g := _v(row, "genreLabel")) and g not in f.setdefault("_genre_labels", []):
            f["_genre_labels"].append(g)
        if (name := _v(row, "director")) and name not in f["directors"]:
            f["directors"].append(name)
        if (name := _v(row, "cast")) and name not in f["cast"]:
            f["cast"].append(name)
    out = []
    for f in films.values():
        genres = normalise_wikidata_genres(f.pop("_genre_labels", []))
        if f["kind"] == "documentary" and "Documentary" not in genres:
            genres.append("Documentary")
        f["genres"] = genres
        f["world_ids"] = assign_worlds(genres, [])
        f["top_tags"] = []
        f["youtube_key"] = sorted(f.pop("youtube_ids"))[0] if f["youtube_ids"] else None
        f["cast_top"] = f["cast"][:5]
        out.append(f)
    return out


async def fetch_recent_de_releases(since: date, client: httpx.AsyncClient, batch: int = 150) -> list[dict]:
    rows = await _sparql(client, _RECENT % since.isoformat())
    qids = sorted({_qid(_v(r, "film")) for r in rows})
    for i in range(0, len(qids), batch):
        values = " ".join(f"wd:{q}" for q in qids[i : i + batch])
        rows += await _sparql(client, _DETAILS % values)
    return fold_recent(rows)
