"""Extended search beyond the catalogue: live title search (Streaming Availability API, incl. DE streaming)
and a person's filmography from Wikidata (newest first). Hits not in the catalogue are imported lazily."""

import logging
import time
from datetime import date, timedelta

import httpx

from cinesense.domain.models import Availability, Movie
from cinesense.ingest.wikidata import HEADERS, SPARQL_URL, USER_AGENT, _qid, _v, _wiki_title
from cinesense.ingest.worlds_map import assign_worlds, normalise_wikidata_genres
from cinesense.providers.streaming import _fresh, images_from_payload, options_from_payload

WBSEARCH_URL = "https://www.wikidata.org/w/api.php"
log = logging.getLogger(__name__)

_FILMOGRAPHY = """
SELECT ?film ?filmLabel ?pub ?imdb ?yt ?enwiki ?role ?genreLabel WHERE {
  { ?film wdt:P161 wd:%(q)s . BIND("cast" AS ?role) }
  UNION { ?film wdt:P57 wd:%(q)s . BIND("director" AS ?role) }
  ?film wdt:P31/wdt:P279* wd:Q11424 .
  OPTIONAL { ?film wdt:P577 ?pub }
  OPTIONAL { ?film wdt:P345 ?imdb }
  OPTIONAL { ?film wdt:P1651 ?yt }
  OPTIONAL { ?film wdt:P136 ?g . ?g rdfs:label ?genreLabel FILTER(LANG(?genreLabel) = "en") }
  OPTIONAL { ?enwiki schema:about ?film ; schema:isPartOf <https://en.wikipedia.org/> }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
} LIMIT 400"""

_PERSON_WORDS = ("actor", "actress", "director", "filmmaker", "screenwriter", "comedian", "performer")


class LiveSearch:
    def __init__(self, streaming, http: httpx.Client | None = None) -> None:
        self.streaming = streaming
        self.http = http or httpx.Client()
        self._people: dict[str, tuple[float, tuple]] = {}  # normalised name -> (time, result), 1 day

    def search_title(self, q: str) -> list[Movie]:
        """1 Streaming Availability request; typo-tolerant, includes DE streaming options and posters."""
        if self.streaming is None:
            return []
        key = f"browse:live-title:{' '.join(q.lower().split())}"  # cached a day (browse_cache table)
        cached = _fresh(self.streaming.store.get(key), timedelta(days=1))
        if cached is None:
            r = self.streaming._request(
                "/shows/search/title",
                {"title": q, "country": "de", "show_type": "movie", "output_language": "en"},
            )
            if r is None or r.status_code != 200:
                return []
            cached = {"shows": r.json()}
            self.streaming.store.put(key, cached)
        out = []
        for show in cached["shows"]:
            if not show.get("imdbId"):
                continue
            self.streaming.store.put(show["imdbId"], show)  # doubles as the per-film cache entry
            out.append(movie_from_show(show))
        return out

    def search_person(self, name: str) -> tuple[str | None, list[Movie]]:
        key = " ".join(name.lower().split())
        hit = self._people.get(key)
        if hit and time.monotonic() - hit[0] < 86_400:
            return hit[1]
        result = self._search_person(name)
        if result[0] is not None:
            self._people[key] = (time.monotonic(), result)
        return result

    def _search_person(self, name: str) -> tuple[str | None, list[Movie]]:
        try:
            r = self.http.get(
                WBSEARCH_URL,
                params={
                    "action": "wbsearchentities",
                    "search": name,
                    "language": "en",
                    "type": "item",
                    "limit": 7,
                    "format": "json",
                },
                headers={"User-Agent": USER_AGENT},
                timeout=10,
            )
            r.raise_for_status()
            candidates = r.json().get("search", [])
            person = next(
                (
                    c
                    for c in candidates
                    if any(w in (c.get("description") or "").lower() for w in _PERSON_WORDS)
                ),
                None,
            )
            if person is None:
                return None, []
            s = self.http.post(
                SPARQL_URL, data={"query": _FILMOGRAPHY % {"q": person["id"]}}, headers=HEADERS, timeout=60
            )
            s.raise_for_status()
            rows = s.json()["results"]["bindings"]
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            log.warning("live person search failed: %s", exc)
            return None, []
        films: dict[str, dict] = {}
        for row in rows:
            qid = _qid(_v(row, "film"))
            f = films.setdefault(qid, {"title": _v(row, "filmLabel"), "pub": None, "genres": []})
            if (p := _v(row, "pub")) and (f["pub"] is None or p < f["pub"]):
                f["pub"] = p
            for key in ("imdb", "yt", "enwiki"):
                f[key] = f.get(key) or _v(row, key)
            if (g := _v(row, "genreLabel")) and g not in f["genres"]:
                f["genres"].append(g)
        movies = []
        for qid, f in films.items():
            if not f["title"] or f["title"] == qid:
                continue
            genres = normalise_wikidata_genres(f["genres"])
            movies.append(
                Movie(
                    id=f"wd-{qid}",
                    title=f["title"],
                    year=int(f["pub"][:4]) if f["pub"] else None,
                    genres=genres,
                    world_ids=assign_worlds(genres, []),
                    imdb_id=f.get("imdb"),
                    wikidata_id=qid,
                    youtube_key=f.get("yt"),
                    wikipedia_title=_wiki_title(f["enwiki"]) if f.get("enwiki") else None,
                    cast_top=[person["label"]],
                )
            )
        movies.sort(key=lambda m: m.year or 0, reverse=True)
        return person["label"], movies


_SA_GENRES = {
    "scifi": "Sci-Fi",
    "action": "Action",
    "adventure": "Adventure",
    "comedy": "Comedy",
    "romance": "Romance",
    "thriller": "Thriller",
    "mystery": "Mystery",
    "crime": "Crime",
    "horror": "Horror",
    "drama": "Drama",
    "animation": "Animation",
    "family": "Children",
    "fantasy": "Fantasy",
    "documentary": "Documentary",
    "war": "War",
    "western": "Western",
    "music": "Musical",
}


def movie_from_show(show: dict) -> Movie:
    genres = [_SA_GENRES[g["id"]] for g in show.get("genres", []) if g.get("id") in _SA_GENRES]
    images = images_from_payload(show)
    return Movie(
        id=f"imdb-{show['imdbId']}",
        title=show.get("title") or show.get("originalTitle") or show["imdbId"],
        kind="documentary" if "Documentary" in genres else "film",
        year=show.get("releaseYear"),
        runtime_min=show.get("runtime"),
        genres=genres,
        world_ids=assign_worlds(genres, []),
        overview=show.get("overview") or "",
        directors=show.get("directors") or [],
        cast_top=(show.get("cast") or [])[:5],
        imdb_id=show["imdbId"],
        poster_url=images.vertical_poster,
        horizontal_poster_url=images.horizontal_poster,
        backdrop_url=images.horizontal_backdrop,
        availability=Availability(streaming_de=options_from_payload(show)),
    )


def recent(m: Movie, days: int = 56) -> bool:
    return bool(m.release_date_de and m.release_date_de >= date.today() - timedelta(days=days))
