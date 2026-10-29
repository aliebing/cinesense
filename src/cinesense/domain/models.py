from typing import Literal

from pydantic import BaseModel, Field


class Availability(BaseModel):
    in_cinema_de: bool = False
    streaming_flatrate_de: list[str] = Field(default_factory=list)


class Movie(BaseModel):
    id: str
    title: str
    year: int | None = None
    runtime_min: int | None = None
    original_language: str
    genres: list[str] = Field(default_factory=list)
    world_ids: list[str] = Field(default_factory=list)
    overview: str = ""
    poster_url: str | None = None
    backdrop_url: str | None = None
    youtube_key: str | None = None
    vote_average: float | None = None
    vote_count: int = 0
    age_rating_de: str | None = None
    availability: Availability = Field(default_factory=Availability)
    is_placeholder: bool = False


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
    min_vote_count: int = 0


class RankedMovie(BaseModel):
    movie: Movie
    score: float
    match_percent: int
