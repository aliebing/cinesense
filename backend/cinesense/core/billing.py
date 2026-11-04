"""Who leads a film: Wikidata lists the cast in no reliable order (a cameo can come before the lead), but the
Wikipedia lead names the main cast in poster order ("starring A, B and C")."""

import re
import unicodedata

UNKNOWN_CAST = 0.8  # no lead text, or the lead names none of the cast
_CAST_LIST = re.compile(r" (star|stars|starring|starred|co stars|features|featuring|ensemble cast) ")


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " " + re.sub(r"[^a-z0-9]+", " ", text.lower()).strip() + " "


def billing_order(lead: str, cast: list[str]) -> dict[str, int]:
    """1-based order in which the lead names each cast member, counted from "stars"/"starring" on; 0 for those it
    doesn't name. Full names first, then a surname that no one else in the cast shares. Empty when the lead names
    nobody (nothing to tell)."""
    text = _norm(lead)
    if m := _CAST_LIST.search(text):  # "written and directed by X. It stars ..." — X is no top billing
        text = text[m.start() :]
    surnames = [_norm(n).split()[-1] if _norm(n).split() else "" for n in cast]
    found: dict[str, int] = {}
    for name, surname in zip(cast, surnames, strict=True):
        pos = text.find(_norm(name))
        if pos < 0 and len(surname) > 3 and surnames.count(surname) == 1:
            pos = text.find(f" {surname} ")
        if pos >= 0:
            found[name] = pos
    if not found:
        return {}
    ranked = sorted(found, key=found.get)
    return {n: (ranked.index(n) + 1 if n in found else 0) for n in cast}


def role_weight(role: str, billing: int | None) -> float:
    """How strongly a film counts for a person search: directors and top-billed actors fully, cameos half."""
    if role != "cast":
        return 1.0
    if billing is None:
        return UNKNOWN_CAST
    if billing == 0:
        return 0.5
    if billing <= 2:
        return 1.0
    return 0.85 if billing == 3 else 0.7


def top_cast(cast: list[str], order: dict[str, int], n: int = 5) -> list[str]:
    """The names shown as a film's leading cast: as billed in the Wikipedia lead, then the rest in Wikidata's
    order (which has no ordinal for most films: Die Hard listed Rick Ducommun before Bruce Willis)."""
    billed = sorted((name for name in cast if order.get(name)), key=lambda name: order[name])
    return (billed + [name for name in cast if not order.get(name)])[:n]
