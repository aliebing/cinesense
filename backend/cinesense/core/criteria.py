"""One shared search state: filled by the chat agent, the chip bar and the advanced search."""

from typing import Literal

from pydantic import BaseModel, Field

MUST_THRESHOLD = 0.6
NOT_THRESHOLD = 0.5


class TagCriterion(BaseModel):
    idx: int = Field(ge=0, lt=1128)
    weight: int = Field(default=5, ge=1, le=10)
    mode: Literal["prefer", "must", "not"] = "prefer"


class SearchCriteria(BaseModel):
    tags: list[TagCriterion] = Field(default_factory=list, max_length=12)
    plot_query: str | None = None
    title: str | None = None
    person: str | None = None
    person_role: Literal["cast", "director", "any"] = "any"
    exclude_genres: list[str] = Field(default_factory=list)
    exclude_people: list[str] = Field(default_factory=list, max_length=5)  # as typed; the person search corrects
    world_id: str | None = None
    availability: Literal["cinema", "stream", "any"] = "any"
    kind: Literal["film", "documentary", "any"] = "any"
    max_runtime_min: int | None = Field(default=None, ge=30, le=400)
    year_from: int | None = None
    year_to: int | None = None
    original_language: str | None = None
    min_rating_count: int = 0
    extended: bool = False

    def prefer_weights(self) -> dict[int, int]:
        """Weights for similarity: prefer and must tags (must also narrows); not-tags never add similarity."""
        return {t.idx: t.weight for t in self.tags if t.mode != "not"}

    def must_tags(self) -> list[int]:
        return [t.idx for t in self.tags if t.mode == "must"]

    def not_tags(self) -> list[int]:
        return [t.idx for t in self.tags if t.mode == "not"]

    def has_tags(self) -> bool:
        return bool(self.tags)

    def has_text_signal(self) -> bool:
        return bool(self.plot_query or self.title or self.person)

    def with_no_horror(self, horror_idx: int, weight: int = 5) -> "SearchCriteria":
        genres = self.exclude_genres if "Horror" in self.exclude_genres else [*self.exclude_genres, "Horror"]
        tags = [t for t in self.tags if t.idx != horror_idx] + [TagCriterion(idx=horror_idx, weight=weight, mode="not")]
        return self.model_copy(update={"exclude_genres": genres, "tags": tags})
