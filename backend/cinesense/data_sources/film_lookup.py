"""A film named by the model, checked against real sources: Wikidata says whether a film of that title (and year)
exists, English Wikipedia gives its plot. Nothing here comes from the model's memory."""

import logging
import re

import httpx

from cinesense.core.models import Movie
from cinesense.core.worlds_map import assign_worlds, normalise_wikidata_genres
from cinesense.data_sources.wikidata import HEADERS, SPARQL_URL, USER_AGENT, _qid, _v, _wiki_title
from cinesense.data_sources.wikipedia import API_URL, extract_plot

WBSEARCH_URL = "https://www.wikidata.org/w/api.php"
PLOT_CHARS = 3000
log = logging.getLogger(__name__)

_FILMS = """
SELECT ?film ?pub ?imdb ?yt ?enwiki ?genreLabel ?dirLabel WHERE {
  VALUES ?film { %s }
  ?film wdt:P31/wdt:P279* wd:Q11424 .
  OPTIONAL { ?film wdt:P577 ?pub }
  OPTIONAL { ?film wdt:P345 ?imdb }
  OPTIONAL { ?film wdt:P1651 ?yt }
  OPTIONAL { ?film wdt:P136 ?g . ?g rdfs:label ?genreLabel FILTER(LANG(?genreLabel) = "en") }
  OPTIONAL { ?film wdt:P57 ?d . ?d rdfs:label ?dirLabel FILTER(LANG(?dirLabel) = "en") }
  OPTIONAL { ?enwiki schema:about ?film ; schema:isPartOf <https://en.wikipedia.org/> }
}"""
_HEADING = re.compile(r"^==[^=]", re.M)


class FilmLookup:
    def __init__(self, http: httpx.Client | None = None) -> None:
        self.http = http or httpx.Client(headers={"User-Agent": USER_AGENT})

    def find(self, title: str, year: int | None = None) -> tuple[Movie, str] | None:
        """The film of this title on Wikidata (the one of that year, ±1, if there are several) and its Wikipedia
        plot (or the article's lead when it has no plot section); None when Wikidata knows no such film."""
        try:
            film = self._film(title, year)
            if film is None:
                return None
            plot = self._plot(film.wikipedia_title) if film.wikipedia_title else ""
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            log.warning("film lookup failed for %r: %s", title, exc)
            return None
        return film, plot

    def _film(self, title: str, year: int | None) -> Movie | None:
        r = self.http.get(
            WBSEARCH_URL,
            params={
                "action": "wbsearchentities",
                "search": title,
                "language": "en",
                "type": "item",
                "limit": 12,
                "format": "json",
            },
            timeout=10,
        )
        r.raise_for_status()
        found = r.json().get("search", [])
        labels = {c["id"]: c.get("label") or title for c in found}
        if not labels:
            return None
        s = self.http.post(
            SPARQL_URL, data={"query": _FILMS % " ".join(f"wd:{q}" for q in labels)}, headers=HEADERS, timeout=30
        )
        s.raise_for_status()
        films: dict[str, dict] = {}
        for row in s.json()["results"]["bindings"]:
            f = films.setdefault(_qid(_v(row, "film")), {"pub": None, "genres": [], "directors": []})
            if (p := _v(row, "pub")) and (f["pub"] is None or p < f["pub"]):
                f["pub"] = p
            for key in ("imdb", "yt", "enwiki"):
                f[key] = f.get(key) or _v(row, key)
            for key, col in (("genres", "genreLabel"), ("directors", "dirLabel")):
                if (val := _v(row, col)) and val not in f[key]:
                    f[key].append(val)
        ranked = [q for q in labels if q in films]  # Wikidata's own order: the best label match first
        if not ranked:
            return None

        def year_of(q: str) -> int | None:
            return int(films[q]["pub"][:4]) if films[q]["pub"] else None

        if year is not None:
            ranked = [q for q in ranked if year_of(q) is not None and abs(year_of(q) - year) <= 1] or ranked
        qid = ranked[0]
        f = films[qid]
        genres = normalise_wikidata_genres(f["genres"])
        return Movie(
            id=f"wd-{qid}",
            title=labels[qid],
            year=year_of(qid),
            genres=genres,
            world_ids=assign_worlds(genres, []),
            directors=f["directors"][:2],
            imdb_id=f.get("imdb"),
            wikidata_id=qid,
            youtube_key=f.get("yt"),
            wikipedia_title=_wiki_title(f["enwiki"]) if f.get("enwiki") else None,
        )

    def _plot(self, article: str) -> str:
        r = self.http.get(
            API_URL,
            params={
                "action": "query",
                "prop": "extracts",
                "explaintext": "1",
                "exsectionformat": "wiki",
                "redirects": "1",
                "titles": article,
                "format": "json",
                "formatversion": "1",
            },
            timeout=20,
        )
        r.raise_for_status()
        page = next(iter(r.json().get("query", {}).get("pages", {}).values()), {})
        text = page.get("extract") or ""
        plot = extract_plot(text) or text[: m.start() if (m := _HEADING.search(text)) else len(text)].strip()
        return plot[:PLOT_CHARS]
