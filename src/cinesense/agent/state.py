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
