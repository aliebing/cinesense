"""Automatic checks for one scenario's final turn. Pure functions over the API's JSON shapes."""

import re

from cinesense.chat_agent.grounding import user_named_titles, validate_titles
from cinesense.evaluation.scenarios import Expect

Check = tuple[bool, list[str]]


def check_constraints(results: list[dict], e: Expect) -> Check:
    if not results:
        return (not e.results_required), ([] if not e.results_required else ["no results"])
    fails = []
    for r in results:
        m, title = r["movie"], r["movie"]["title"]
        if e.max_runtime and m.get("runtime_min") and m["runtime_min"] > e.max_runtime:
            fails.append(f"{title}: {m['runtime_min']} min > {e.max_runtime}")
        if bad := [g for g in m.get("genres", []) if g in e.exclude_genres]:
            fails.append(f"{title}: excluded genre {', '.join(bad)}")
        if e.kind and m.get("kind") != e.kind:
            fails.append(f"{title}: kind {m.get('kind')}")
        if e.year_from and (m.get("year") is None or m["year"] < e.year_from):
            fails.append(f"{title}: year {m.get('year')} < {e.year_from}")
        if e.person:
            people = [p.lower() for p in m.get("directors", []) + m.get("cast_top", [])]
            people += [x[5:].lower() for x in r.get("reasons", []) if x.startswith("with ")]  # full-cast match
            if e.person.lower() not in people:
                fails.append(f"{title}: without {e.person} in the top-billed people")
        a = m.get("availability") or {}
        if e.availability == "stream" and a.get("streaming_de") is not None and not a.get("subscription_services"):
            fails.append(f"{title}: known not streaming")  # unknown availability is labelled in the UI, not a lie
        if e.availability == "cinema" and not a.get("in_cinema_de"):
            fails.append(f"{title}: not in cinemas")
    return not fails, fails


def check_tools(called: list[str], e: Expect) -> Check:
    fails = []
    if e.tools_any and not set(called) & set(e.tools_any):
        fails.append(f"expected one of {e.tools_any}, called {called}")
    if used := sorted(set(called) & set(e.tools_none)):
        fails.append(f"should not call {used}")
    return not fails, fails


def check_grounding(
    reply: str, results: list[dict], catalogue_titles: set[str], user_text: str, tag_spans: list[str] = ()
) -> Check:
    """tag_spans: the tags of the final search and the proposals — the same rule as the production guard."""
    allowed = [r["movie"]["title"] for r in results] + user_named_titles(user_text, catalogue_titles)
    ok, bad = validate_titles(reply, allowed, catalogue_titles, tag_spans)
    return ok, [f"unlisted title: {t}" for t in bad]


def check_reply(reply: str, e: Expect) -> Check:
    if not e.reply_contains_any:
        return True, []
    low = reply.lower()
    ok = any(s.lower() in low for s in e.reply_contains_any)
    return ok, [] if ok else [f"reply lacks any of {e.reply_contains_any}"]


def title_hit(results: list[dict], e: Expect) -> bool | None:
    if not e.titles_any:
        return None
    titles = {r["movie"]["title"] for r in results}
    return bool(titles & set(e.titles_any))


_STREAM_CLAIM = re.compile(
    r"\b(you can stream|to stream|streams on|streaming on|available to stream|can be streamed)\b", re.I
)
_HEDGE = re.compile(r"not confirmed|unknown|couldn.t (check|confirm)|can.t confirm|unable to confirm", re.I)


def check_availability_claims(reply: str, results: list[dict]) -> Check:
    """A reply may only say films stream when at least one result has known subscription streaming."""
    known = any((r["movie"].get("availability") or {}).get("subscription_services") for r in results)
    if _STREAM_CLAIM.search(reply) and not known and not _HEDGE.search(reply):
        return False, ["claims streaming without known availability"]
    return True, []


def check_relaxed(relaxed: list[str], e: Expect) -> Check:
    if e.relaxed is None or bool(relaxed) == e.relaxed:
        return True, []
    return False, ["expected a widened search" if e.relaxed else "widened without need"]


def check_guarded(guarded: bool, e: Expect) -> Check:
    if e.guarded is None or guarded == e.guarded:
        return True, []
    return False, ["attack reached the model" if e.guarded else "harmless wish was blocked"]


def applies(kind: str, e: Expect) -> bool:
    """Whether a check has anything to test in this scenario (for honest k/n reporting)."""
    if kind == "constraints":
        return bool(e.max_runtime or e.exclude_genres or e.kind or e.availability or e.year_from or e.person)
    if kind == "tools":
        return bool(e.tools_any or e.tools_none)
    if kind == "reply":
        return bool(e.reply_contains_any)
    if kind == "relaxed":
        return e.relaxed is not None
    if kind == "guarded":
        return e.guarded is not None
    return True
