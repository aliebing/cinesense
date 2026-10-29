from typing import Protocol

from cinesense.domain.models import Movie


class MovieProvider(Protocol):
    def list_movies(self) -> list[Movie]: ...

    def get_movie(self, movie_id: str) -> Movie | None: ...
