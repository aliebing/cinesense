"""English Wikipedia: plot sections for RAG (CC BY-SA 4.0; each film links back to its article) and the article's
lead image as the film's poster (film posters there are non-free, used under fair use; only the link is stored,
the image stays on Wikimedia)."""

import asyncio
import re
import time

import httpx

from cinesense.data_sources.wikidata import USER_AGENT

API_URL = "https://en.wikipedia.org/w/api.php"
_PLOT_HEADINGS = ("plot", "synopsis", "premise", "plot summary", "summary", "content", "contents")
_HEADING = re.compile(r"^(={2,})\s*(.*?)\s*\1\s*$", re.M)


def extract_plot(extract: str) -> str | None:
    """Text of the first level-2 plot-like section (sub-headings dropped), or None."""
    matches = list(_HEADING.finditer(extract))
    for i, m in enumerate(matches):
        if len(m.group(1)) == 2 and m.group(2).strip().lower() in _PLOT_HEADINGS:
            end = next((n.start() for n in matches[i + 1 :] if len(n.group(1)) == 2), len(extract))
            body = _HEADING.sub("", extract[m.end() : end])
            body = re.sub(r"\n{3,}", "\n\n", body).strip()
            return body or None
    return None


async def fetch_plot(title: str, client: httpx.AsyncClient, retries: int = 4) -> str | None:
    params = {
        "action": "query",
        "prop": "extracts|pageprops",
        "explaintext": "1",
        "exsectionformat": "wiki",
        "redirects": "1",
        "titles": title,
        "format": "json",
        "formatversion": "1",
    }
    for attempt in range(retries):
        r = await client.get(API_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=30)
        if r.status_code in (429, 500, 502, 503, 504):
            await asyncio.sleep(2**attempt * 2)
            continue
        r.raise_for_status()
        pages = r.json().get("query", {}).get("pages", {})
        page = next(iter(pages.values()), {})
        if "missing" in page or "disambiguation" in page.get("pageprops", {}):
            return None
        return extract_plot(page.get("extract", ""))
    r.raise_for_status()  # still rate-limited or failing: an error (retried next run), not "no plot"
    return None


def chunk_text(text: str, max_chars: int = 900, overlap: int = 120) -> list[str]:
    """Split on paragraph/sentence boundaries into chunks ≤ max_chars with a word overlap."""
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []
    sentences = [s for p in text.split("\n\n") for s in re.split(r"(?<=[.!?])\s+", p.strip()) if s]
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        while len(sentence) > max_chars:  # very long sentence: cut on a word boundary
            cut = sentence.rfind(" ", 0, max_chars)
            cut = cut if cut > 0 else max_chars
            sentences_part, sentence = sentence[:cut], sentence[cut:].strip()
            if current:
                chunks.append(current)
                current = ""
            chunks.append(sentences_part)
        if len(current) + len(sentence) + 1 <= max_chars:
            current = f"{current} {sentence}".strip()
        else:
            chunks.append(current)
            tail = current[-overlap:]
            tail = tail[tail.find(" ") + 1 :] if " " in tail else ""
            current = f"{tail} {sentence}".strip()
            if len(current) > max_chars:
                current = sentence
    if current:
        chunks.append(current)
    return chunks


_INFOBOX_LANGUAGE = re.compile(r"^\s*\|\s*language\s*=(.*?)(?=^\s*\||^\s*\}\})", re.M | re.S | re.I)


def infobox_language(wikitext: str) -> str | None:
    """The first language in a film infobox ("| language = {{Plainlist|* German * Polish}}" -> "German"). The
    infobox lists the primary language first (Template:Infobox film: "only the primary language")."""
    m = _INFOBOX_LANGUAGE.search(wikitext)
    if not m:
        return None
    value = re.sub(r"<!--.*?-->|<ref[^>]*/>|<ref.*?</ref>", "", m.group(1), flags=re.S)
    value = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", value)  # [[Hindi language|Hindi]] -> Hindi
    value = re.sub(r"\{\{\s*(?:plain ?list|ubl|unbulleted list|flatlist|hlist)\s*\|", "", value, flags=re.I)
    for part in re.split(r"<br\s*/?>|\n|\*|\||,|\band\b|/", value):
        name = re.sub(r"[{}()\[\]]", "", part).strip()
        if name and re.fullmatch(r"[A-Za-z][A-Za-z \-']*", name):
            return name.removesuffix(" language").strip()
    return None


async def fetch_infobox_language(title: str, client: httpx.AsyncClient, retries: int = 4) -> str | None:
    """The primary language named in an English Wikipedia film article's infobox, or None."""
    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "rvsection": "0",
        "redirects": "1",
        "titles": title,
        "format": "json",
        "formatversion": "2",
    }
    for attempt in range(retries):
        r = await client.get(API_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=30)
        if r.status_code in (429, 500, 502, 503, 504):
            await asyncio.sleep(2**attempt * 2)
            continue
        r.raise_for_status()
        page = (r.json().get("query", {}).get("pages") or [{}])[0]
        text = (page.get("revisions") or [{}])[0].get("slots", {}).get("main", {}).get("content", "")
        return infobox_language(text)
    return None  # still failing: no hint, the other rules decide


POSTER_MIN_RATIO = 1.2  # height / width: a poster is portrait; a landscape scene photo or a logo is not one


def posters_from_query(data: dict, asked: list[str]) -> dict[str, str]:
    """Poster urls by the titles asked for, from a prop=pageimages answer (formatversion 2), following
    normalisation and redirects. Only portrait images count; tracking parameters are dropped."""
    q = data.get("query", {})
    step = {n["from"]: n["to"] for n in q.get("normalized", [])} | {r["from"]: r["to"] for r in q.get("redirects", [])}
    by_title = {}
    for page in q.get("pages", []):
        thumb = page.get("thumbnail") or {}
        w, h = thumb.get("width") or 0, thumb.get("height") or 0
        if thumb.get("source") and w and h / w >= POSTER_MIN_RATIO:
            by_title[page["title"]] = thumb["source"].split("?", 1)[0]
    out = {}
    for title in asked:
        final, seen = title, set()
        while final in step and final not in seen:  # normalised, then redirected
            seen.add(final)
            final = step[final]
        if final in by_title:
            out[title] = by_title[final]
    return out


def fetch_posters(titles: list[str], client: httpx.Client, retries: int = 4) -> dict[str, str]:
    """Lead images of up to 50 articles in one request (no key, no quota)."""
    params = {
        "action": "query",
        "prop": "pageimages",
        "piprop": "thumbnail",
        "pithumbsize": "480",
        "pilicense": "any",  # film posters are non-free; without this the API leaves them out
        "pilimit": "50",
        "redirects": "1",
        "titles": "|".join(titles),
        "format": "json",
        "formatversion": "2",
    }
    for attempt in range(retries):
        r = client.get(API_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=30)
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(2**attempt * 2)
            continue
        r.raise_for_status()
        return posters_from_query(r.json(), titles)
    r.raise_for_status()
    return {}
