"""The interface every catalogue source implements (Postgres in production, a JSON fixture offline)."""

from typing import Protocol

from cinesense.core.models import Movie


class MovieProvider(Protocol):
    def list_movies(self) -> list[Movie]: ...

    def get_movie(self, movie_id: str) -> Movie | None: ...
