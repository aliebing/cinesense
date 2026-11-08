"""The shared data model: films, availability, mood worlds and ranked results (Pydantic, also the API's JSON)."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, computed_field

StreamingType = Literal["subscription", "rent", "buy", "addon", "free"]
INCLUDED_TYPES = ("subscription", "free")  # watchable at no extra cost: flat rate or free with ads

# DE services as the Streaming Availability API names them, with the names people use for them
SERVICE_ALIASES = {
    "Prime Video": ("prime video", "amazon prime video", "amazon prime", "prime", "amazon", "freevee"),
    "Netflix": ("netflix",),
    "Disney+": ("disney+", "disney plus", "disney"),
    "Apple TV": ("apple tv", "apple tv+", "apple tv plus", "apple"),
    "HBO Max": ("hbo max", "hbo", "max"),
    "Paramount+": ("paramount+", "paramount plus", "paramount"),
    "Wow": ("wow", "sky wow", "sky"),
    "RTL+": ("rtl+", "rtl plus", "rtl"),
    "Mubi": ("mubi",),
    "Pluto TV": ("pluto tv", "pluto"),
    "Crunchyroll": ("crunchyroll",),
    "Zee5": ("zee5",),
    "Curiosity Stream": ("curiosity stream", "curiositystream"),
}


def canonical_service(name: str) -> str | None:
    """The API's name for a streaming service as people write it ("Amazon Prime" -> "Prime Video"); None if unknown."""
    key = " ".join(name.lower().split())
    return next((canon for canon, aliases in SERVICE_ALIASES.items() if key in aliases), None)


class StreamingOption(BaseModel):
    service: str
    type: StreamingType
    link: str | None = None


class Availability(BaseModel):
    in_cinema_de: bool = False
    # None = unknown (not looked up, budget exhausted or source down); [] = known: not streaming
    streaming_de: list[StreamingOption] | None = None

    @computed_field
    @property
    def subscription_services(self) -> list[str]:
        """Services that stream the film at no extra cost (flat rate or free); rent, buy and add-ons don't count."""
        seen: list[str] = []
        for o in self.streaming_de or []:
            if o.type in INCLUDED_TYPES and o.service not in seen:
                seen.append(o.service)
        return seen

    def streams_on(self, services: list[str]) -> bool:
        """Known to stream at no extra cost, on one of `services` when any are named."""
        included = self.subscription_services
        return bool(included) and (not services or any(s in included for s in services))


class Movie(BaseModel):
    id: str
    title: str
    title_de: str | None = None  # German title from Wikidata (live imports), searchable and shown on the stage
    kind: Literal["film", "documentary"] = "film"
    year: int | None = None
    runtime_min: int | None = None
    original_language: str | None = None
    genres: list[str] = Field(default_factory=list)
    world_ids: list[str] = Field(default_factory=list)
    top_tags: list[str] = Field(default_factory=list)
    overview: str = ""
    directors: list[str] = Field(default_factory=list)
    cast_top: list[str] = Field(default_factory=list)
    movielens_id: int | None = None
    imdb_id: str | None = None
    wikidata_id: str | None = None
    wikipedia_title: str | None = None
    release_date_de: date | None = None
    poster_url: str | None = None
    horizontal_poster_url: str | None = None
    backdrop_url: str | None = None
    youtube_key: str | None = None
    ml_rating: float | None = None  # MovieLens average, 0–5
    ml_rating_count: int = 0
    availability: Availability = Field(default_factory=Availability)
    is_placeholder: bool = False
    images_checked: bool = False  # images were looked up once (found or not) — don't spend API calls again


class MoodWorld(BaseModel):
    id: str
    title: str
    kicker: str
    subtitle: str
    tint: str
    genres: list[str]


class RankedMovie(BaseModel):
    movie: Movie
    score: float
    match_percent: int
    reasons: list[str] = Field(default_factory=list)
    misses: list[str] = Field(default_factory=list)  # parts of the original wish a widened search's film misses
