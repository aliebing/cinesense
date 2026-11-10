"""LangGraph agent: ReAct loop (agent <-> tools), then a deterministic search run (present) and a grounded
explanation (explain). Ranking, filters, budgets and grounding are deterministic; the model only decides
the criteria."""

import logging
import threading
from collections import defaultdict
from collections.abc import Callable

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from cinesense.chat_agent.grounding import (
    pick_count,
    result_titles,
    template_answer,
    user_named_titles,
    validate_titles,
)
from cinesense.chat_agent.guard import GUARD_REPLY, leaks_prompt, looks_like_injection, sanitize
from cinesense.chat_agent.prompts import AGENT_PROMPT, EXPLAIN_PROMPT, RELAX_PROMPT
from cinesense.chat_agent.state import AgentState
from cinesense.core.criteria import SearchCriteria
from cinesense.search import widening

MAX_ROUNDS = 6
MAX_RELAX_ROUNDS = 2  # offers to widen a thin search per turn
FALLBACK_REPLY = "Sorry, I didn’t get that — could you say it differently?"
_thread_locks: defaultdict[str, threading.Lock] = defaultdict(threading.Lock)
_locks_guard = threading.Lock()
log = logging.getLogger(__name__)
RESULTS = 8


def criteria_summary(criteria: dict, tags: list[str]) -> str:
    c = SearchCriteria(**(criteria or {}))
    parts = [f"{tags[t.idx] if t.idx < len(tags) else t.idx} ({t.mode}, {t.weight})" for t in c.tags]
    out = [f"tags: {', '.join(parts)}"] if parts else []
    for field in (
        "plot_query",
        "title",
        "person",
        "world_id",
        "max_runtime_min",
        "year_from",
        "year_to",
        "original_language",
        "min_rating",
    ):
        if getattr(c, field):
            out.append(f"{field}: {getattr(c, field)}")
    for field in ("availability", "kind"):
        if getattr(c, field) != "any":
            out.append(f"{field}: {getattr(c, field)}")
    if c.streaming_services:
        out.append(f"streaming services: {', '.join(c.streaming_services)}")
    if c.exclude_genres:
        out.append(f"exclude genres: {', '.join(c.exclude_genres)}")
    if c.exclude_people:
        out.append(f"without: {', '.join(c.exclude_people)}")
    return "; ".join(out) or "(empty)"


def _add_usage(usage: dict, msg) -> dict:
    meta = getattr(msg, "usage_metadata", None) or {}
    return {
        "input_tokens": usage.get("input_tokens", 0) + meta.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0) + meta.get("output_tokens", 0),
    }


HISTORY_TURNS = 8  # user turns the model sees; older ones stay in memory but are not resent


def trim_history(messages: list, max_turns: int = HISTORY_TURNS) -> list:
    """The last max_turns user turns, cut at a user message so tool calls and their answers stay together."""
    starts = [i for i, m in enumerate(messages) if isinstance(m, HumanMessage)]
    return messages if len(starts) <= max_turns else messages[starts[-max_turns] :]


def _profile_kw(state: dict) -> dict:
    from cinesense.taste.profile import Profile

    return {"profile": Profile(**state["profile"])} if state.get("profile") else {}


def _last_human(messages: list) -> str:
    return next((m.content for m in reversed(messages) if isinstance(m, HumanMessage)), "")


def build_graph(llm, explain_llm, tools: list, service, provider, checkpointer):
    agent_llm = llm.bind_tools(tools)
    catalogue: set[str] = set()

    def catalogue_titles() -> set[str]:
        if not catalogue:  # loaded once per process; lazily imported films are only missing from grounding
            titles = {m.title for m in provider.list_movies()}
            catalogue.update(titles)  # one atomic update; readers get the full set or build their own
            return titles
        return catalogue

    def agent(state: AgentState) -> dict:
        system = SystemMessage(
            AGENT_PROMPT.format(criteria=criteria_summary(state.get("criteria"), provider.list_tags()))
        )
        messages = [system, *trim_history(state["messages"])]
        if options := state.get("relax_options"):
            # sent, not stored: the request must end with a user message (the provider rejects a trailing
            # assistant message), but the offer is no wish of the user's and stays out of the history
            lines = "\n".join(f"- {o['id']}: {o['label']} ({o['count']})" for o in options)
            note = RELAX_PROMPT.format(found=len(state.get("results") or []), options=lines).strip()
            messages.append(HumanMessage(f"[CineSense system note] {note}"))
        msg = agent_llm.invoke(messages)
        prompts = {**(state.get("prompts") or {}), "agent": str(system.content)}
        return {"messages": [msg], "usage": _add_usage(state.get("usage") or {}, msg), "prompts": prompts}

    def tick(state: AgentState) -> dict:
        return {"rounds": state.get("rounds", 0) + 1}

    by_name = {t.name: t for t in tools}

    def run_tools(state: AgentState) -> dict:
        """Run the model's tool calls one after another, each on the state left by the previous one
        (parallel calls would race on the shared criteria)."""
        current = dict(state)
        update: dict = {"messages": []}
        for call in state["messages"][-1].tool_calls:
            if current.get("relax_options") and call["name"] != "relax_search":
                # an offered widening is decided first; other changes would mix into (or undo) it
                note = "Not run: first choose one of the offered options with relax_search."
                update["messages"].append(ToolMessage(note, tool_call_id=call["id"]))
                continue
            injected = {**call, "type": "tool_call", "args": {**call["args"], "state": current}}
            try:
                result = by_name[call["name"]].invoke(injected)
            except Exception as exc:  # noqa: BLE001 — the model sees the error and can retry
                result = Command(
                    update={"messages": [ToolMessage(f"Error: {exc}"[:300], tool_call_id=call["id"], status="error")]}
                )
            changes = (
                dict(result.update)
                if isinstance(result, Command)
                else {"messages": [ToolMessage(str(result), tool_call_id=call["id"])]}
            )
            update["messages"] += changes.pop("messages", [])
            current.update(changes)
            update.update(changes)
        return update

    def after_tools(state: AgentState) -> str:
        """A widening goes straight to the search: back at the model, it tends to tighten the criteria again."""
        last_ai = next(m for m in reversed(state["messages"]) if isinstance(m, AIMessage))
        widened = any(c["name"] == "relax_search" for c in last_ai.tool_calls) and not state.get("relax_options")
        return "present" if widened else "agent"

    def route(state: AgentState) -> str:
        last = state["messages"][-1]
        if state.get("relax_options") and not getattr(last, "tool_calls", None):
            return "auto_relax"  # offered a relaxation but the model did not pick one
        if getattr(last, "tool_calls", None):
            # round limit reached: present with the current criteria (it also answers the open calls)
            return "tick" if state.get("rounds", 0) < MAX_ROUNDS else "present"
        return "present" if state.get("criteria_changed") else END

    def present(state: AgentState) -> dict:
        update: dict = {"messages": []}
        last = state["messages"][-1]
        if getattr(last, "tool_calls", None):  # every tool call needs an answer, or the next turn is rejected
            update["messages"] = [
                ToolMessage("Not run: tool limit reached.", tool_call_id=c["id"]) for c in last.tool_calls
            ]
        try:
            c = SearchCriteria(**(state.get("criteria") or {}))
            update["one_mood"] = None
            result = service.run(c, 0, RESULTS, **_profile_kw(state))
            items = result.items
            if state.get("original_criteria"):
                widening.mark_misses(items, SearchCriteria(**state["original_criteria"]), provider)
            elif items and all(r.match_percent < widening.STRONG_PERCENT for r in items):
                # like the search page: no film carries every mood, so the films that fit at least one of them
                found = widening.one_mood_at_a_time(
                    lambda one: service.run(one, 0, 50, **_profile_kw(state)).items, c, provider.list_tags()
                )
                if found is not None:
                    items = found[0][:RESULTS]
                    widening.mark_misses(items, c, provider, c.model_copy(update={"tags": []}))
                    update["one_mood"] = [{"tag": p.tag, "count": p.count} for p in found[1]]
            update["results"] = [r.model_dump(mode="json") for r in items]
        except Exception:  # noqa: BLE001 — keep the history valid; explain answers with "no films"
            log.exception("present: search failed")
            update["results"] = []
            return update
        update["mood_gaps"] = _mood_gaps(items[: pick_count(update["results"])], state)
        return update

    def _mood_gaps(top: list, state: AgentState) -> dict:
        """Wanted moods the presented films miss (against the wish before any widening)."""
        try:
            c = SearchCriteria(**(state.get("original_criteria") or state.get("criteria") or {}))
            cov = widening.mood_coverage(top, c, provider)
        except Exception:  # noqa: BLE001 — without the check the reply only loses the note
            log.exception("present: mood coverage failed")
            return {}
        names = provider.list_tags()
        wanted = [names[t.idx] for t in c.tags if t.mode != "not" and t.idx < len(names)]
        split = wanted if not cov.missing and not cov.combined and len(wanted) > 1 else []
        return {"missing": cov.missing, "split": split}

    def verify(state: AgentState) -> dict:
        """Too few films: work out which constraints could be widened and how many films each would find."""
        results = state.get("results") or []
        rounds = state.get("relax_rounds", 0)
        if len(results) >= widening.MIN_RESULTS or rounds >= MAX_RELAX_ROUNDS:
            return {"relax_options": []}
        try:
            c = SearchCriteria(**(state.get("criteria") or {}))
            options = widening.probe(service, c, provider.list_tags(), current=len(results))
        except Exception:  # noqa: BLE001 — no options; explain answers with what was found
            log.exception("verify: probing relaxations failed")
            options = []
        if not options:
            return {"relax_options": []}
        return {
            "relax_options": [{"id": o.id, "label": o.label, "count": o.count} for o in options],
            "relax_rounds": rounds + 1,
        }

    def after_verify(state: AgentState) -> str:
        return "agent" if state.get("relax_options") else "explain"

    def auto_relax(state: AgentState) -> dict:
        """Deterministic choice when the model did not pick: the least intrusive option that finds enough."""
        offered = [
            widening.Relaxation(o["id"], o["label"], SearchCriteria(), o["count"]) for o in state["relax_options"]
        ]
        best = widening.pick_auto(offered)
        opt = (
            widening.apply(SearchCriteria(**(state.get("criteria") or {})), best.id, provider.list_tags())
            if best
            else None
        )
        if opt is None:
            return {"relax_options": []}
        return widening.applied_update(state, opt)

    def explain(state: AgentState) -> dict:
        results = state.get("results") or []
        relaxed = state.get("relaxed") or []
        gaps = state.get("mood_gaps") or {}
        wish = _last_human(state["messages"])
        if not results:
            return {"messages": [AIMessage(template_answer([], relaxed))]}

        def german(m: dict) -> str:  # German users may know a film only by its German title ("Winnetou 1. Teil")
            de = m.get("title_de")
            return f" [German title: {de}]" if de and de != m["title"] else ""

        listing = "\n".join(
            f"- {r['movie']['title']}{german(r['movie'])} ({r['movie'].get('year')}): "
            f"{'; '.join(r.get('reasons', []))}. Plot: {(r['movie'].get('overview') or '')[:220]}"
            for r in results
        )
        prompt = (
            f"Wish: {wish}\nCriteria: {criteria_summary(state.get('criteria'), provider.list_tags())}\n"
            f"Results:\n{listing}"
        )
        if relaxed:
            prompt += f"\nWidened: {'; '.join(relaxed)}"
        if gaps.get("missing"):
            prompt += f"\nNot met by the top films: {', '.join(gaps['missing'])}"
        if gaps.get("split"):
            prompt += f"\nNo top film combines: {', '.join(gaps['split'])}"
        if state.get("one_mood"):
            parts = ", ".join(f"{p['tag']} ({p['count']})" for p in state["one_mood"])
            prompt += "\nEach fits one mood: no film carries all the moods together; shown are films that fit one: "
            prompt += parts
        usage = state.get("usage") or {}
        system = SystemMessage(EXPLAIN_PROMPT.format(picks=pick_count(results)))
        prompts = {**(state.get("prompts") or {}), "explain": str(system.content), "explain_input": prompt}
        try:
            msg = explain_llm.invoke([system, HumanMessage(prompt)])
            text, usage = str(msg.content), _add_usage(usage, msg)
            if msg.response_metadata.get("finish_reason") == "length":
                text = ""  # cut off mid-sentence
        except Exception:  # noqa: BLE001 — the template is always a valid answer
            text = ""
        titles = catalogue_titles()
        allowed = result_titles(results) + user_named_titles(wish, titles)
        names = provider.list_tags()
        tag_spans = [names[t["idx"]] for t in (state.get("criteria") or {}).get("tags", []) if t["idx"] < len(names)]
        tag_spans += [p["tag"] for p in state.get("proposals") or []]
        ok, bad = validate_titles(text, allowed, titles, tag_spans, listing) if text else (False, ["(empty answer)"])
        if not ok:
            log.warning("grounding fallback, unlisted titles: %s", bad)
            return {
                "messages": [AIMessage(template_answer(results, relaxed, gaps))],
                "grounding_fallback": True,
                "grounding_reason": bad or ["no usable answer (error or cut off)"],
                "usage": usage,
                "prompts": prompts,
            }
        return {"messages": [AIMessage(text)], "usage": usage, "prompts": prompts}

    g = StateGraph(AgentState)
    g.add_node("agent", agent)
    g.add_node("tick", tick)
    g.add_node("tools", run_tools)
    g.add_node("present", present)
    g.add_node("verify", verify)
    g.add_node("auto_relax", auto_relax)
    g.add_node("explain", explain)
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", route, ["tick", "present", "auto_relax", END])
    g.add_edge("tick", "tools")
    g.add_conditional_edges("tools", after_tools, ["agent", "present"])
    g.add_edge("present", "verify")
    g.add_conditional_edges("verify", after_verify, ["agent", "explain"])
    g.add_edge("auto_relax", "present")
    g.add_edge("explain", END)
    return g.compile(checkpointer=checkpointer)


TOOL_STATUS = {
    "set_mood_tags": "Setting mood tags…",
    "set_filters": "Applying filters…",
    "search_plot": "Searching plots…",
    "find": "Looking it up…",
    "similar_to": "Finding similar moods…",
    "new_search": "Starting a new search…",
    "film_info": "Reading film facts…",
    "propose_exclusions": "Suggesting exclusions…",
    "show_on_stage": "Preparing the stage…",
    "relax_search": "Widening the search…",
}


def run_turn(
    graph,
    thread_id: str,
    message: str,
    ui_criteria: dict,
    on_status: Callable[[str], None] | None = None,
    profile=None,
) -> dict:
    """One chat turn. The UI's chips are the truth: they seed the criteria; per-turn fields are reset."""
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 4 * MAX_ROUNDS + 30}
    message = sanitize(message)
    if looks_like_injection(message):  # never reaches the model, and stays out of the history
        log.warning("prompt injection blocked on thread %s", thread_id)
        return _guarded_turn(graph, config, ui_criteria)
    inputs = {
        "messages": [HumanMessage(message)],
        "criteria": SearchCriteria(**(ui_criteria or {})).model_dump(),
        "criteria_changed": False,
        "results": [],
        "proposals": [],
        "handoff": None,
        "streaming_checks": 0,
        "rounds": 0,
        "usage": {},
        "grounding_fallback": False,
        "grounding_reason": [],
        "prompts": {},
        "profile": profile.model_dump() if profile is not None else None,
        "relax_rounds": 0,
        "one_mood": None,
        "relax_options": [],
        "relaxed": [],
        "original_criteria": None,
        "mood_gaps": {},
    }
    with _locks_guard:
        lock = _thread_locks[thread_id]
    with lock:  # one turn at a time per conversation (two tabs, page change mid-turn)
        return _run_locked(graph, config, inputs, on_status)


def _run_locked(graph, config: dict, inputs: dict, on_status) -> dict:
    tools_called: list[str] = []
    tool_errors = 0
    trace: list[dict] = []  # each tool call with its arguments and (shortened) result, for /api/inspect
    by_id: dict[str, dict] = {}
    for update in graph.stream(inputs, config, stream_mode="updates"):
        if "agent" in update:
            for call in getattr(update["agent"]["messages"][-1], "tool_calls", None) or []:
                tools_called.append(call["name"])
                entry = {"name": call["name"], "args": call.get("args", {}), "result": None}
                trace.append(entry)
                by_id[call.get("id", "")] = entry
                if on_status:
                    on_status(TOOL_STATUS.get(call["name"], "Thinking…"))
        if "tools" in update:
            tool_errors += sum(getattr(m, "status", "") == "error" for m in update["tools"].get("messages", []))
            for m in update["tools"].get("messages", []):
                if (entry := by_id.get(getattr(m, "tool_call_id", ""))) is not None:
                    entry["result"] = str(m.content)[:800]
        if on_status and "present" in update:
            on_status("Ranking films…")
    s = graph.get_state(config).values
    reply = str(s["messages"][-1].content).strip() or FALLBACK_REPLY
    guarded = leaks_prompt(reply, [AGENT_PROMPT, EXPLAIN_PROMPT, RELAX_PROMPT])
    if guarded:  # the model quoted its instructions: replace the reply, in the history too
        log.warning("prompt leak blocked on thread %s", config["configurable"]["thread_id"])
        reply = GUARD_REPLY
        graph.update_state(config, {"messages": [AIMessage(reply, id=s["messages"][-1].id)]}, as_node="explain")
    return {
        "reply": reply,
        "guarded": guarded,
        "criteria": s.get("criteria"),
        "results": s.get("results", []),
        "picks": pick_count(s.get("results", [])),  # how many results the reply presents (3-5)
        "tool_trace": trace,
        "prompts": s.get("prompts", {}),
        "proposals": s.get("proposals", []),
        "handoff": s.get("handoff"),
        "usage": s.get("usage", {}),
        "rounds": s.get("rounds", 0),
        "grounding_fallback": s.get("grounding_fallback", False),
        "grounding_reason": s.get("grounding_reason", []),
        "relaxed": s.get("relaxed", []),
        "mood_gaps": s.get("mood_gaps") or {},
        "history_len": len(s["messages"]),
        "tools_called": tools_called,
        "tool_errors": tool_errors,
    }


def _guarded_turn(graph, config: dict, ui_criteria: dict) -> dict:
    """The answer to a blocked message: a fixed reply, the chips unchanged, no model call, no tools."""
    history = graph.get_state(config).values.get("messages") or []
    return {
        "reply": GUARD_REPLY,
        "guarded": True,
        "criteria": SearchCriteria(**(ui_criteria or {})).model_dump(),
        "results": [],
        "picks": 0,
        "tool_trace": [],
        "prompts": {},
        "proposals": [],
        "handoff": None,
        "usage": {},
        "rounds": 0,
        "grounding_fallback": False,
        "grounding_reason": [],
        "relaxed": [],
        "mood_gaps": {},
        "history_len": len(history),
        "tools_called": [],
        "tool_errors": 0,
    }
