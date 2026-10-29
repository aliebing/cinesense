"""Agent tools. Each one is a small, testable method on ToolKit returning (state update, message for the model);
make_tools() wraps them as LangChain tools that write the update into the graph state (LangGraph Command)."""

from typing import Annotated, Literal

from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from pydantic import BaseModel, Field

from cinesense.agent.tags import resolve_tags
from cinesense.domain.criteria import SearchCriteria
from cinesense.domain.models import Movie

STREAMING_PER_TURN = 3
FILTER_FIELDS = (
    "availability",
    "max_runtime_min",
    "kind",
    "year_from",
    "year_to",
    "original_language",
    "exclude_genres",
)


class TagSpec(BaseModel):
    name: str = Field(description="Mood tag in plain English, e.g. 'dark', 'space travel', 'medieval', 'funny'")
    weight: int = Field(default=6, ge=1, le=10, description="Importance 1-10")
    mode: Literal["prefer", "must", "not"] = Field(
        default="prefer", description="prefer re-ranks, must narrows, not excludes"
    )


class ToolKit:
    def __init__(self, service, provider, streaming) -> None:
        self.service = service
        self.provider = provider
        self.streaming = streaming

    # --- helpers ----------------------------------------------------------
    @staticmethod
    def _criteria(state: dict) -> SearchCriteria:
        return SearchCriteria(**(state.get("criteria") or {}))

    def _find_film(self, title: str) -> Movie | None:
        scores = self.provider.search_title(title)
        if not scores:
            return None
        movies = (
            {m.id: m for m in self.provider.get_many(list(scores)[:10])} if hasattr(self.provider, "get_many") else {}
        )
        best = max(scores, key=lambda i: (scores[i], movies[i].ml_rating_count if i in movies else 0))
        return movies.get(best) or self.provider.get_movie(best)

    # --- tools ------------------------------------------------------------
    def set_mood_tags(self, state: dict, tags: list[dict], replace: bool = False) -> tuple[dict, str]:
        c = self._criteria(state)
        specs = [TagSpec(**t) for t in tags]
        resolved, unresolved = resolve_tags([s.name for s in specs], self.provider.list_tags())
        current = [] if replace else [t.model_dump() for t in c.tags]
        added = []
        for spec, (tag, idx) in zip([s for s in specs if s.name not in unresolved], resolved, strict=True):
            current = [t for t in current if t["idx"] != idx] + [{"idx": idx, "weight": spec.weight, "mode": spec.mode}]
            added.append(f"{tag} ({spec.mode}, {spec.weight})")
        c = SearchCriteria(**{**c.model_dump(), "tags": current[-12:]})
        msg = f"Mood tags now: {', '.join(added) or 'unchanged'}."
        if unresolved:
            msg += f" Not found as tags: {', '.join(unresolved)} — use plot search for those."
        return {"criteria": c.model_dump(), "criteria_changed": True}, msg

    def set_filters(self, state: dict, filters: dict) -> tuple[dict, str]:
        c = self._criteria(state).model_dump()
        for field in filters.get("clear") or []:
            if field in FILTER_FIELDS:
                c[field] = [] if field == "exclude_genres" else ("any" if field in ("availability", "kind") else None)
        for k, v in filters.items():
            if k in FILTER_FIELDS and v is not None:
                c[k] = v
        c = SearchCriteria(**c).model_dump()
        shown = {k: c[k] for k in FILTER_FIELDS if c[k] not in (None, [], "any")}
        return {"criteria": c, "criteria_changed": True}, f"Filters now: {shown or 'none'}."

    def search_plot(self, state: dict, query: str) -> tuple[dict, str]:
        c = self._criteria(state).model_copy(update={"plot_query": query})
        preview = self.service.run(SearchCriteria(plot_query=query), 0, 5).items
        lines = [f"- {r.movie.title} ({r.movie.year}): {(r.reasons[0] if r.reasons else '')[:120]}" for r in preview]
        return {
            "criteria": c.model_dump(),
            "criteria_changed": True,
        }, "Plot search set. Top matches:\n" + "\n".join(lines or ["(none yet)"])

    def find_person(self, state: dict, name: str, role: str = "any") -> tuple[dict, str]:
        scores, names = self.provider.search_person(name, role)
        resolved = next(iter(names.values()), name)
        c = self._criteria(state).model_copy(update={"person": resolved, "person_role": role})
        return {
            "criteria": c.model_dump(),
            "criteria_changed": True,
        }, f"Person set to {resolved}: {len(scores)} films in the catalogue."

    def similar_to(self, state: dict, title: str) -> tuple[dict, str]:
        film = self._find_film(title)
        if film is None:
            return {}, f"No film found for '{title}'."
        c = self._criteria(state)
        idx = {t: i for i, t in enumerate(self.provider.list_tags())}
        tags = [t.model_dump() for t in c.tags]
        for name in film.top_tags[:5]:
            if name in idx and all(t["idx"] != idx[name] for t in tags):
                tags.append({"idx": idx[name], "weight": 6, "mode": "prefer"})
        c = SearchCriteria(**{**c.model_dump(), "tags": tags[-12:]})
        return (
            {"criteria": c.model_dump(), "criteria_changed": True},
            f"Using the mood of {film.title} ({film.year}): {', '.join(film.top_tags[:5])}.",
        )

    def check_streaming(self, state: dict, title: str) -> tuple[dict, str]:
        used = state.get("streaming_checks", 0)
        if used >= STREAMING_PER_TURN:
            return {}, "Streaming check limit for this turn reached."
        film = self._find_film(title)
        if film is None or not film.imdb_id or self.streaming is None:
            return {"streaming_checks": used}, f"Streaming availability for '{title}' is unknown."
        options = self.streaming.get_de(film.imdb_id)
        upd = {"streaming_checks": used + 1}
        if options is None:
            return upd, f"Streaming availability for {film.title} is unknown right now."
        subs = sorted({o.service for o in options if o.type == "subscription"})
        return upd, f"{film.title} in Germany: " + (
            f"subscription on {', '.join(subs)}" if subs else "not on a subscription service"
        )

    def film_facts(self, state: dict, title: str) -> tuple[dict, str]:
        f = self._find_film(title)
        if f is None:
            return {}, f"No film found for '{title}'."
        return {}, (
            f"{f.title} ({f.year}), {f.runtime_min or '?'} min, genres {', '.join(f.genres)}; "
            f"directed by {', '.join(f.directors[:2]) or '?'}; with {', '.join(f.cast_top[:3]) or '?'}; "
            f"MovieLens {f.ml_rating or '?'} ({f.ml_rating_count} ratings); mood: {', '.join(f.top_tags)}. "
            f"Plot: {f.overview[:300]}"
        )

    def propose_exclusions(self, state: dict, tags: list[str]) -> tuple[dict, str]:
        resolved, _ = resolve_tags(tags, self.provider.list_tags())
        existing = {p["idx"] for p in state.get("proposals", [])}
        proposals = list(state.get("proposals", [])) + [
            {"idx": i, "tag": t, "mode": "not"} for t, i in resolved if i not in existing
        ]
        return {"proposals": proposals}, f"Proposed (not applied): {', '.join(t for t, _ in resolved) or 'none'}."

    def show_on_stage(self, state: dict, title: str) -> tuple[dict, str]:
        film = self._find_film(title)
        if film is None:
            return {}, f"No film found for '{title}'."
        world = (state.get("criteria") or {}).get("world_id") or (film.world_ids[0] if film.world_ids else "suspense")
        return {"handoff": {"world_id": world, "film_id": film.id}}, f"{film.title} will be shown on stage."


def make_tools(kit: ToolKit) -> list:
    def wrap(update: dict, msg: str, call_id: str) -> Command:
        return Command(update={**update, "messages": [ToolMessage(msg, tool_call_id=call_id)]})

    @tool
    def set_mood_tags(
        tags: list[TagSpec],
        state: Annotated[dict, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
        replace: bool = False,
    ) -> Command:
        """Set mood tags (Tag Genome) with weight and mode. Use mode 'not' for clear exclusions like 'no horror'."""
        return wrap(
            *kit.set_mood_tags(state, [t.model_dump() if isinstance(t, BaseModel) else t for t in tags], replace),
            tool_call_id,
        )

    @tool
    def set_filters(
        state: Annotated[dict, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
        availability: Literal["cinema", "stream", "any"] | None = None,
        max_runtime_min: int | None = None,
        kind: Literal["film", "documentary", "any"] | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        original_language: str | None = None,
        exclude_genres: list[str] | None = None,
        clear: list[str] | None = None,
    ) -> Command:
        """Set hard filters: availability in Germany, max runtime (minutes), kind, year range, ISO 639-1 original
        language (e.g. 'en'), excluded MovieLens genres (e.g. ['Horror']). 'clear' resets named filters."""
        filters = {k: v for k, v in locals().items() if k not in ("state", "tool_call_id")}
        return wrap(*kit.set_filters(state, filters), tool_call_id)

    @tool
    def search_plot(
        query: str, state: Annotated[dict, InjectedState], tool_call_id: Annotated[str, InjectedToolCallId]
    ) -> Command:
        """Semantic search over Wikipedia plots (RAG) for themes, settings or story ideas,
        e.g. 'astronaut alone in space'."""
        return wrap(*kit.search_plot(state, query), tool_call_id)

    @tool
    def find_person(
        name: str,
        state: Annotated[dict, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
        role: Literal["cast", "director", "any"] = "any",
    ) -> Command:
        """Restrict to films with an actor or director (typo-tolerant)."""
        return wrap(*kit.find_person(state, name, role), tool_call_id)

    @tool
    def similar_to(
        title: str, state: Annotated[dict, InjectedState], tool_call_id: Annotated[str, InjectedToolCallId]
    ) -> Command:
        """Use the mood tags of a known film, for requests like 'something like Interstellar'."""
        return wrap(*kit.similar_to(state, title), tool_call_id)

    @tool
    def check_streaming(
        title: str, state: Annotated[dict, InjectedState], tool_call_id: Annotated[str, InjectedToolCallId]
    ) -> Command:
        """Check where one film streams in Germany (max 3 per turn)."""
        return wrap(*kit.check_streaming(state, title), tool_call_id)

    @tool
    def film_facts(
        title: str, state: Annotated[dict, InjectedState], tool_call_id: Annotated[str, InjectedToolCallId]
    ) -> Command:
        """Facts about one film from the catalogue (year, runtime, people, rating, mood, plot)."""
        return wrap(*kit.film_facts(state, title), tool_call_id)

    @tool
    def propose_exclusions(
        tags: list[str],
        state: Annotated[dict, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        """Suggest extra exclusions for vague wishes ('nothing scary' -> ['scary', 'creepy']).
        Not applied; the user decides."""
        return wrap(*kit.propose_exclusions(state, tags), tool_call_id)

    @tool
    def show_on_stage(
        title: str, state: Annotated[dict, InjectedState], tool_call_id: Annotated[str, InjectedToolCallId]
    ) -> Command:
        """When the user picks or confirms a film, show it on the genre stage."""
        return wrap(*kit.show_on_stage(state, title), tool_call_id)

    return [
        set_mood_tags,
        set_filters,
        search_plot,
        find_person,
        similar_to,
        check_streaming,
        film_facts,
        propose_exclusions,
        show_on_stage,
    ]
