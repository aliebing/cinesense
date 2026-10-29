"""LangGraph agent: ReAct loop (agent <-> tools), then a deterministic search run (present) and a grounded
explanation (explain). Ranking, filters, budgets and grounding are deterministic; the model only decides
the criteria."""

import re
from collections.abc import Callable

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from cinesense.agent.grounding import mentioned_titles, template_answer, validate_titles
from cinesense.agent.prompts import AGENT_PROMPT, EXPLAIN_PROMPT
from cinesense.agent.state import AgentState
from cinesense.domain.criteria import SearchCriteria

MAX_ROUNDS = 6
RESULTS = 8
_ASKS_FOR_FILMS = re.compile(r"\b(show|recommend|suggest|list|more|films?|movies?|docs?|documentar\w*)\b", re.I)


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
    ):
        if getattr(c, field):
            out.append(f"{field}: {getattr(c, field)}")
    for field in ("availability", "kind"):
        if getattr(c, field) != "any":
            out.append(f"{field}: {getattr(c, field)}")
    if c.exclude_genres:
        out.append(f"exclude genres: {', '.join(c.exclude_genres)}")
    return "; ".join(out) or "(empty)"


def _add_usage(usage: dict, msg) -> dict:
    meta = getattr(msg, "usage_metadata", None) or {}
    return {
        "input_tokens": usage.get("input_tokens", 0) + meta.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0) + meta.get("output_tokens", 0),
    }


def _last_human(messages: list) -> str:
    return next((m.content for m in reversed(messages) if isinstance(m, HumanMessage)), "")


def build_graph(llm, explain_llm, tools: list, service, provider, checkpointer):
    agent_llm = llm.bind_tools(tools)
    catalogue: set[str] = set()

    def catalogue_titles() -> set[str]:
        if not catalogue:  # loaded once per process; lazily imported films are only missing from grounding
            catalogue.update(m.title for m in provider.list_movies())
        return catalogue

    def agent(state: AgentState) -> dict:
        system = SystemMessage(
            AGENT_PROMPT.format(criteria=criteria_summary(state.get("criteria"), provider.list_tags()))
        )
        msg = agent_llm.invoke([system, *state["messages"]])
        return {"messages": [msg], "usage": _add_usage(state.get("usage") or {}, msg)}

    def tick(state: AgentState) -> dict:
        return {"rounds": state.get("rounds", 0) + 1}

    def route(state: AgentState) -> str:
        last = state["messages"][-1]
        if getattr(last, "tool_calls", None) and state.get("rounds", 0) < MAX_ROUNDS:
            return "tick"
        if state.get("criteria_changed"):
            return "present"
        if _ASKS_FOR_FILMS.search(_last_human(state["messages"])) and not str(last.content).strip().endswith("?"):
            return "present"
        return END

    def present(state: AgentState) -> dict:
        update: dict = {}
        last = state["messages"][-1]
        if getattr(last, "tool_calls", None):  # round limit: every tool call still needs an answer in history
            update["messages"] = [
                ToolMessage("Not run: tool limit reached.", tool_call_id=c["id"]) for c in last.tool_calls
            ]
        result = service.run(SearchCriteria(**(state.get("criteria") or {})), 0, RESULTS)
        update["results"] = [r.model_dump(mode="json") for r in result.items]
        return update

    def explain(state: AgentState) -> dict:
        results = state.get("results") or []
        wish = _last_human(state["messages"])
        if not results:
            return {"messages": [AIMessage(template_answer([]))]}
        listing = "\n".join(
            f"- {r['movie']['title']} ({r['movie'].get('year')}): {'; '.join(r.get('reasons', []))}. "
            f"Plot: {(r['movie'].get('overview') or '')[:220]}"
            for r in results
        )
        prompt = (
            f"Wish: {wish}\nCriteria: {criteria_summary(state.get('criteria'), provider.list_tags())}\n"
            f"Results:\n{listing}"
        )
        usage = state.get("usage") or {}
        try:
            msg = explain_llm.invoke([SystemMessage(EXPLAIN_PROMPT), HumanMessage(prompt)])
            text, usage = str(msg.content), _add_usage(usage, msg)
        except Exception:  # noqa: BLE001 — the template is always a valid answer
            text = ""
        titles = catalogue_titles()
        allowed = [r["movie"]["title"] for r in results] + mentioned_titles(wish, titles)
        ok, _ = validate_titles(text, allowed, titles) if text else (False, [])
        if not ok:
            return {"messages": [AIMessage(template_answer(results))], "grounding_fallback": True, "usage": usage}
        return {"messages": [AIMessage(text)], "usage": usage}

    g = StateGraph(AgentState)
    g.add_node("agent", agent)
    g.add_node("tick", tick)
    g.add_node("tools", ToolNode(tools))
    g.add_node("present", present)
    g.add_node("explain", explain)
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", route, ["tick", "present", END])
    g.add_edge("tick", "tools")
    g.add_edge("tools", "agent")
    g.add_edge("present", "explain")
    g.add_edge("explain", END)
    return g.compile(checkpointer=checkpointer)


TOOL_STATUS = {
    "set_mood_tags": "Setting mood tags…",
    "set_filters": "Applying filters…",
    "search_plot": "Searching plots…",
    "find_person": "Looking up people…",
    "similar_to": "Finding similar moods…",
    "check_streaming": "Checking streaming in Germany…",
    "film_facts": "Reading film facts…",
    "propose_exclusions": "Suggesting exclusions…",
    "show_on_stage": "Preparing the stage…",
}


def run_turn(
    graph, thread_id: str, message: str, ui_criteria: dict, on_status: Callable[[str], None] | None = None
) -> dict:
    """One chat turn. The UI's chips are the truth: they seed the criteria; per-turn fields are reset."""
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 4 * MAX_ROUNDS + 10}
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
    }
    for update in graph.stream(inputs, config, stream_mode="updates"):
        if on_status and "agent" in update:
            for call in getattr(update["agent"]["messages"][-1], "tool_calls", None) or []:
                on_status(TOOL_STATUS.get(call["name"], "Thinking…"))
        if on_status and "present" in update:
            on_status("Ranking films…")
    s = graph.get_state(config).values
    return {
        "reply": str(s["messages"][-1].content),
        "criteria": s.get("criteria"),
        "results": s.get("results", []),
        "proposals": s.get("proposals", []),
        "handoff": s.get("handoff"),
        "usage": s.get("usage", {}),
        "rounds": s.get("rounds", 0),
        "grounding_fallback": s.get("grounding_fallback", False),
        "history_len": len(s["messages"]),
    }
