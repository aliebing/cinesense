"""Grounding: the explanation may only name films from the result list (or ones the user named).
Anything else falls back to a deterministic template answer."""

import re

_EMPHASIS = re.compile(r"\*\*(.+?)\*\*|(?<!\*)\*(?!\*)(.+?)\*|_(.+?)_|\"(.+?)\"|“(.+?)”")
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


def validate_titles(
    text: str, allowed_titles: list[str], catalogue_titles: set[str], tag_spans: list[str] = ()
) -> tuple[bool, list[str]]:
    """tag_spans: mood tags of the current search; an emphasised span that is exactly such a tag ("**creepy**")
    is a tag, not a film. Tags never take part in the substring check, so they cannot hide real titles."""
    tags = {_norm(t) for t in tag_spans}
    allowed = {_norm(t) for t in allowed_titles}
    catalogue = {_norm(t): t for t in catalogue_titles}
    bad: list[str] = []
    for m in _EMPHASIS.finditer(text):
        span = next(g for g in m.groups() if g).strip()
        key = _norm(re.sub(r"\(\d{4}\)$", "", span))
        if key in tags:
            continue
        if key not in allowed and (key in catalogue or _looks_like_title(span)):
            bad.append(catalogue.get(key, span))
    stripped = text
    for t in sorted(allowed_titles, key=len, reverse=True):  # "The Matrix Reloaded" must not match "The Matrix"
        stripped = re.sub(rf"(?<!\w){re.escape(t)}(?!\w)", " ", stripped, flags=re.IGNORECASE)
    for t in mentioned_titles(stripped, catalogue_titles):
        if _norm(t) not in allowed and t not in bad:
            bad.append(t)
    return not bad, bad


def template_answer(results: list[dict]) -> str:
    if not results:
        return "No films match all of these wishes — try removing a must tag or a filter."
    lines = []
    for r in results[:5]:
        m = r["movie"]
        year = f" ({m['year']})" if m.get("year") else ""
        why = ", ".join(r.get("reasons", [])[:2])
        lines.append(f"- **{m['title']}**{year}" + (f" — {why}" if why else ""))
    return "Here are films that match:\n" + "\n".join(lines)
