from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from cinesense.api.deps import get_provider
from cinesense.domain.models import MoodWorld, Movie, MovieQuery, RankedMovie
from cinesense.domain.worlds import WORLDS, get_world
from cinesense.providers.base import MovieProvider
from cinesense.recommend.baseline import rank_baseline

Provider = Annotated[MovieProvider, Depends(get_provider)]

HOME_TILES_PER_WORLD = 4
HOME_TITLES_PER_WORLD = 2


def _home(provider: MovieProvider) -> dict:
    movies = provider.list_movies()
    per_world = [rank_baseline(movies, MovieQuery(world_id=w.id)) for w in WORLDS]
    tiles: list[Movie] = []
    seen: set[str] = set()
    # Round-robin across worlds so every world is represented on the homepage.
    for i in range(max(len(r) for r in per_world)):
        for ranked in per_world:
            if i < len(ranked) and ranked[i].movie.id not in seen and len(tiles) < 6 * HOME_TILES_PER_WORLD:
                tiles.append(ranked[i].movie)
                seen.add(ranked[i].movie.id)
    titles = [r.movie.title for ranked in per_world for r in ranked[:HOME_TITLES_PER_WORLD]]
    return {"worlds": list(WORLDS), "tiles": tiles, "titles": titles}


def create_app() -> FastAPI:
    app = FastAPI(title="CineSense API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/worlds")
    def worlds() -> list[MoodWorld]:
        return list(WORLDS)

    @app.get("/api/worlds/{world_id}/movies")
    def world_movies(
        world_id: str, provider: Provider, limit: Annotated[int, Query(ge=1, le=100)] = 12
    ) -> list[RankedMovie]:
        if get_world(world_id) is None:
            raise HTTPException(status_code=404, detail="world_not_found")
        return rank_baseline(provider.list_movies(), MovieQuery(world_id=world_id))[:limit]

    @app.get("/api/movies/{movie_id}")
    def movie(movie_id: str, provider: Provider) -> Movie:
        found = provider.get_movie(movie_id)
        if found is None:
            raise HTTPException(status_code=404, detail="movie_not_found")
        return found

    @app.get("/api/movies/{movie_id}/related")
    def related(
        movie_id: str, provider: Provider, limit: Annotated[int, Query(ge=1, le=100)] = 13
    ) -> list[RankedMovie]:
        found = provider.get_movie(movie_id)
        if found is None:
            raise HTTPException(status_code=404, detail="movie_not_found")
        world_id = found.world_ids[0] if found.world_ids else None
        ranked = rank_baseline(provider.list_movies(), MovieQuery(world_id=world_id))
        return [r for r in ranked if r.movie.id != movie_id][:limit]

    @app.get("/api/home")
    def home(provider: Provider) -> dict:
        return _home(provider)

    return app
