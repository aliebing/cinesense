from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, computed_field

StreamingType = Literal["subscription", "rent", "buy", "addon", "free"]


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
        seen: list[str] = []
        for o in self.streaming_de or []:
            if o.type == "subscription" and o.service not in seen:
                seen.append(o.service)
        return seen


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


class MovieQuery(BaseModel):
    world_id: str | None = None
    original_language: str | None = None
    exclude_genres: list[str] = Field(default_factory=list)
    max_runtime_min: int | None = None
    availability: Literal["cinema", "stream", "any"] = "any"
    min_rating_count: int = 0


class RankedMovie(BaseModel):
    movie: Movie
    score: float
    match_percent: int
    reasons: list[str] = Field(default_factory=list)
