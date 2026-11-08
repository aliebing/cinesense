"""Grounding: the explanation may only name films from the result list (or ones the user named).
Anything else falls back to a deterministic template answer."""

import re

_EMPHASIS = re.compile(r"\*\*(.+?)\*\*|(?<!\*)\*(?!\*)(.+?)\*|(?<!\w)_(.+?)_(?!\w)|\"(.+?)\"|“(.+?)”")
_STOP = {"the", "a", "an", "of", "in", "on", "and", "to", "for", "at", "it", "is", "my", "me", "you", "up", "time"}


def _norm(s: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", s.lower()).split())


def _looks_like_title(span: str) -> bool:
    words = span.split()
    return 2 <= len(words) <= 8 and all(w[:1].isupper() or w.lower() in _STOP for w in words)


def mentioned_titles(text: str, catalogue_titles: set[str]) -> list[str]:
    """Catalogue titles with at least two non-trivial words that appear in title case in the text."""
    found = []
    for t in catalogue_titles:
        words = t.split()
        if len(words) < 2 or all(w.lower() in _STOP for w in words) or t not in text:
            continue
        if re.search(rf"(?<!\w){re.escape(t)}(?!\w)", text):
            found.append(t)
    return found


def user_named_titles(text: str, catalogue_titles: set[str]) -> list[str]:
    """Catalogue titles the user wrote, including single-word ones ("Alien"), matched case-insensitively."""
    by_norm = {}
    for t in catalogue_titles:
        by_norm.setdefault(_norm(t), t)
    words = _norm(text).split()
    found = []
    for n in range(1, 9):
        for i in range(len(words) - n + 1):
            key = " ".join(words[i : i + n])
            if key in by_norm and by_norm[key] not in found and (n > 1 or key not in _STOP):
                found.append(by_norm[key])
    return found


_ALT_TITLE = re.compile(r"\s*\([^()]*\)$")  # "Let the Right One In (Låt den rätte komma in)", "Seven (a.k.a. Se7en)"


def result_titles(results: list[dict]) -> list[str]:
    """The names a reply may use for the result films: the catalogue title, the title without its trailing
    alternative title in brackets (how people write it), and the German title."""
    out: list[str] = []
    for r in results:
        m = r["movie"]
        for t in (m["title"], _ALT_TITLE.sub("", m["title"]), m.get("title_de")):
            if t and t not in out:
                out.append(t)
    return out


def validate_titles(
    text: str,
    allowed_titles: list[str],
    catalogue_titles: set[str],
    tag_spans: list[str] = (),
    source_text: str = "",
) -> tuple[bool, list[str]]:
    """tag_spans: mood tags of the current search; an emphasised span that is exactly such a tag ("**creepy**")
    is a tag, not a film. Tags never take part in the substring check, so they cannot hide real titles.
    source_text: the plots the model was given; a catalogue title in it ("race to Silver City") may be repeated
    in running text as the place or name it is there, but never emphasised like a film."""
    tags = {_norm(t) for t in tag_spans}
    allowed = {_norm(t) for t in allowed_titles}
    catalogue = {_norm(t): t for t in catalogue_titles}
    bad: list[str] = []
    for m in _EMPHASIS.finditer(text):
        span = next(g for g in m.groups() if g).strip()
        if m.lastindex and m.lastindex >= 4 and len(span.split()) < 2:
            continue  # a quoted single word ("Mother") is a name or a word, rarely a film reference
        key = _norm(re.sub(r"\(\d{4}\)$", "", span))
        if key in tags:
            continue
        if key not in allowed and (key in catalogue or _looks_like_title(span)):
            bad.append(catalogue.get(key, span))
    stripped = text
    for t in sorted(allowed_titles, key=len, reverse=True):  # "The Matrix Reloaded" must not match "The Matrix"
        stripped = re.sub(rf"(?<!\w){re.escape(t)}(?!\w)", " ", stripped, flags=re.IGNORECASE)
    in_source = set(mentioned_titles(source_text, catalogue_titles)) if source_text else set()
    for t in mentioned_titles(stripped, catalogue_titles):
        if _norm(t) not in allowed and t not in bad and t not in in_source:
            bad.append(t)
    return not bad, bad


PICKS_MIN, PICKS_MAX, PICKS_MARGIN = 3, 5, 3  # the chat names 3-5 films: all within 3 points of the best


def pick_count(results: list[dict]) -> int:
    """How many of the ranked results the chat presents as its picks: at least three, up to five when the fourth
    and fifth match nearly as well as the best (match_percent at most PICKS_MARGIN points lower)."""
    if not results:
        return 0
    best = results[0].get("match_percent", 0)
    close = sum(1 for r in results[:PICKS_MAX] if r.get("match_percent", 0) >= best - PICKS_MARGIN)
    return min(len(results), max(PICKS_MIN, close))


def template_answer(results: list[dict], relaxed: list[str] = (), gaps: dict | None = None) -> str:
    widened = f"Nothing matched every wish, so I widened the search: {'; '.join(relaxed)}.\n" if relaxed else ""
    gaps = gaps or {}
    if results and gaps.get("missing"):
        widened += f"None of the top films is clearly {' or '.join(gaps['missing'])}.\n"
    elif results and gaps.get("split"):
        widened += f"No top film combines {' and '.join(gaps['split'])}; each covers part of the wish.\n"
    if not results:
        return widened + "No films match all of these wishes — try removing a must tag or a filter."
    lines = []
    for r in results[: pick_count(results)]:
        m = r["movie"]
        year = f" ({m['year']})" if m.get("year") else ""
        why = ", ".join(r.get("reasons", [])[:2])
        lines.append(f"- **{m['title']}**{year}" + (f" — {why}" if why else ""))
    return widened + "Here are films that match:\n" + "\n".join(lines)
