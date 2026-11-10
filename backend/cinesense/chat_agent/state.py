"""The LangGraph state of one conversation: messages, the shared criteria and per-turn bookkeeping."""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    criteria: dict  # SearchCriteria JSON — the shared, visible search state
    criteria_changed: bool
    results: list[dict]  # RankedMovie JSON (≤ 8) from the deterministic present node
    proposals: list[dict]  # {idx, tag, mode: "not"} suggested, never applied silently
    handoff: dict | None  # {world_id, film_id}
    streaming_checks: int
    rounds: int
    usage: dict  # input_tokens, output_tokens
    grounding_fallback: bool
    grounding_reason: list[str]  # why the template answer was used
    profile: dict | None  # Profile JSON (👍/👎 taste) used by the deterministic search
    prompts: dict  # what this turn sent: agent system prompt, explain system prompt and input (for /api/inspect)
    relax_rounds: int  # how often this turn offered to widen a thin search
    relax_options: list[dict]  # {id, label, count} offered to the model right now; empty when none pending
    relaxed: list[str]  # labels of the relaxations applied this turn, in order
    original_criteria: dict | None  # the criteria before the first relaxation (to mark what results miss)
    mood_gaps: dict  # {missing: [...], split: [...]}: wanted moods the presented films miss or never combine
    one_mood: list[dict] | None  # {tag, count}: no film carried every mood, the results fit one each
