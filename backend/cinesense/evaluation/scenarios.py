"""Evaluation scenarios (evaluation/scenarios.json): what the user says and what a correct answer satisfies."""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from cinesense.core.config import REPO_ROOT

SCENARIOS_PATH = REPO_ROOT / "evaluation" / "scenarios.json"
Failure = Literal["streaming_down", "budget_exhausted", "embeddings_down", "live_down"]


class Expect(BaseModel):
    tools_any: list[str] = Field(default_factory=list)  # at least one of these tools must be called
    tools_none: list[str] = Field(default_factory=list)
    max_runtime: int | None = None
    exclude_genres: list[str] = Field(default_factory=list)
    exclude_people: list[str] = Field(default_factory=list)  # none of them among a result's top-billed people
    kind: Literal["film", "documentary"] | None = None
    availability: Literal["cinema", "stream"] | None = None
    year_from: int | None = None
    person: str | None = None
    results_required: bool = True
    titles_any: list[str] = Field(default_factory=list)  # informative "hit" check, not a constraint
    reply_contains_any: list[str] = Field(default_factory=list)
    relaxed: bool | None = None  # True: the search must be widened; False: it must not be
    guarded: bool | None = None  # True: the injection guard must block the message; False: it must let it through


class Scenario(BaseModel):
    id: str
    category: str
    turns: list[str] = Field(min_length=1)
    ui_criteria: dict = Field(default_factory=dict)
    expect: Expect = Field(default_factory=Expect)
    failure: Failure | None = None


def load_scenarios(path: Path = SCENARIOS_PATH) -> list[Scenario]:
    return [Scenario(**s) for s in json.loads(path.read_text(encoding="utf-8"))]
