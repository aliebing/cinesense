"""English Wikipedia (CC BY-SA 4.0) plot sections for RAG; each film links back to its article."""

import asyncio
import re

import httpx

from cinesense.ingest.wikidata import USER_AGENT

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
