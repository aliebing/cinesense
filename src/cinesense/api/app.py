from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from cinesense.api.chat import router as chat_router
from cinesense.api.deps import (
    get_embedder,
    get_live,
    get_provider,
    get_streaming,
    get_trailer_checker,
    get_trailers,
)
from cinesense.api.images import with_images as _with_images
from cinesense.api.personal import UserProfile
from cinesense.api.personal import router as personal_router
from cinesense.config import load_env_file
from cinesense.domain.criteria import SearchCriteria
from cinesense.domain.models import MoodWorld, Movie, RankedMovie
from cinesense.domain.worlds import WORLDS, get_world
from cinesense.search.service import SearchService

Provider = Annotated[object, Depends(get_provider)]
Streaming = Annotated[object, Depends(get_streaming)]
Embedder = Annotated[object, Depends(get_embedder)]
Live = Annotated[object, Depends(get_live)]
Trailers = Annotated[object, Depends(get_trailers)]
Checker = Annotated[object, Depends(get_trailer_checker)]

ROW_SIZE = 16
IMAGE_FILL = 12  # images fetched per list response (each new film costs one Streaming API request once)
RELATED_IMAGE_FILL = 24  # the related row shows up to 24 films; no blank tiles


class DiscoverRequest(BaseModel):
    criteria: SearchCriteria = Field(default_factory=SearchCriteria)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=50)


class DiscoverResponse(BaseModel):
    items: list[RankedMovie]
    total: int
    hidden_by_exclusion: int = 0
    extended_used: bool = False


def create_app(load_env: bool = True) -> FastAPI:
    if load_env:
        load_env_file()
    app = FastAPI(title="CineSense API")
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat_router)
    app.include_router(personal_router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/worlds")
    def worlds() -> list[MoodWorld]:
        return list(WORLDS)

    @app.get("/api/tags")
    def tags(provider: Provider) -> list[dict]:
        return [{"idx": i, "tag": t} for i, t in enumerate(provider.list_tags())]

    def _discover(
        req: DiscoverRequest, provider, streaming, embedder, live=None, tasks=None, profile=None, checker=None
    ) -> DiscoverResponse:
        res = SearchService(provider, streaming, embedder, live).run(req.criteria, req.offset, req.limit, profile)
        if checker is not None:
            checker.filter_playable([r.movie for r in res.items])
        for r in res.items[:IMAGE_FILL]:
            _with_images(r.movie, provider, streaming)
        if res.extended_used and tasks is not None:
            from cinesense.ingest.pipeline import enrich_new_films

            new_ids = [r.movie.id for r in res.items if r.movie.id.startswith(("wd-", "imdb-"))]
            tasks.add_task(enrich_new_films, new_ids)
        return DiscoverResponse(
            items=res.items,
            total=res.total,
            hidden_by_exclusion=res.hidden_by_exclusion,
            extended_used=res.extended_used,
        )

    @app.post("/api/discover")
    def discover(
        req: DiscoverRequest,
        provider: Provider,
        streaming: Streaming,
        embedder: Embedder,
        profile: UserProfile,
        checker: Checker,
    ) -> DiscoverResponse:
        return _discover(req, provider, streaming, embedder, profile=profile, checker=checker)

    @app.post("/api/search")
    def search(
        req: DiscoverRequest,
        provider: Provider,
        streaming: Streaming,
        embedder: Embedder,
        live: Live,
        tasks: BackgroundTasks,
        profile: UserProfile,
        checker: Checker,
    ) -> DiscoverResponse:
        return _discover(req, provider, streaming, embedder, live, tasks, profile, checker)

    @app.get("/api/worlds/{world_id}/movies")
    def world_movies(
        world_id: str, provider: Provider, profile: UserProfile, limit: Annotated[int, Query(ge=1, le=100)] = 12
    ) -> list[RankedMovie]:
        if get_world(world_id) is None:
            raise HTTPException(status_code=404, detail="world_not_found")
        # with the profile: a rejected film never comes back as the world's default stage film
        return SearchService(provider).run(SearchCriteria(world_id=world_id), 0, limit, profile).items

    @app.get("/api/movies/{movie_id}")
    def movie(movie_id: str, provider: Provider, streaming: Streaming, trailers: Trailers, checker: Checker) -> Movie:
        found = provider.get_movie(movie_id)
        if found is None:
            raise HTTPException(status_code=404, detail="movie_not_found")
        if checker is not None:
            checker.filter_playable([found])
        if found.youtube_key is None and trailers is not None:  # Wikidata trailer ids win when they play
            found.youtube_key = trailers.find_trailer(found.id, found.title, found.year)
        if streaming is not None and found.imdb_id:
            found.availability.streaming_de = streaming.get_de(found.imdb_id)
        return _with_images(found, provider, streaming)

    @app.get("/api/movies/{movie_id}/related")
    def related(
        movie_id: str,
        provider: Provider,
        streaming: Streaming,
        profile: UserProfile,
        checker: Checker,
        limit: Annotated[int, Query(ge=1, le=100)] = 13,
        world_id: str | None = None,
    ) -> list[RankedMovie]:
        found = provider.get_movie(movie_id)
        if found is None:
            raise HTTPException(status_code=404, detail="movie_not_found")
        # Rank within the world the user is browsing; fall back to the film's first world.
        if world_id is None or get_world(world_id) is None:
            world_id = found.world_ids[0] if found.world_ids else None
        items = SearchService(provider).run(SearchCriteria(world_id=world_id), 0, limit + 1, profile).items
        items = [r for r in items if r.movie.id != movie_id][:limit]
        if checker is not None:
            checker.filter_playable([r.movie for r in items])
        for r in items[:RELATED_IMAGE_FILL]:
            _with_images(r.movie, provider, streaming)
        return items

    class TrailerReport(BaseModel):
        video_id: str = Field(pattern=r"^[A-Za-z0-9_-]{6,20}$")

    @app.post("/api/trailers/report", status_code=204)
    def report_trailer(req: TrailerReport, checker: Checker) -> None:
        """The embedded player could not play this trailer (deleted, blocked in Germany, embedding off)."""
        if checker is not None:
            checker.mark_bad(req.video_id)

    @app.get("/api/home")
    def home(provider: Provider, streaming: Streaming, checker: Checker) -> dict:
        movies = provider.list_movies()
        pools: dict[str, list[Movie]] = {}
        for w in WORLDS:
            in_world = sorted((m for m in movies if w.id in m.world_ids), key=lambda m: m.ml_rating_count, reverse=True)
            pool = [m.model_copy(deep=True) for m in in_world[: ROW_SIZE * 4]]
            if checker is not None:
                checker.filter_playable(pool)
            # popular films with a playable trailer first, so hovering a tile usually plays something
            pools[w.id] = sorted(pool, key=lambda m: (m.youtube_key is not None, m.ml_rating_count), reverse=True)
        rows: dict[str, list[Movie]] = {w.id: [] for w in WORLDS}
        used: set[str] = set()  # each film in one row only; worlds take turns so none is starved
        for _ in range(ROW_SIZE):
            for w in WORLDS:
                nxt = next((m for m in pools[w.id] if m.id not in used), None)
                if nxt is not None:
                    rows[w.id].append(nxt)
                    used.add(nxt.id)
        for w in WORLDS:
            rows[w.id] = [_with_images(m, provider, streaming) for m in rows[w.id]]
        titles = []
        for w in WORLDS:
            titles += [m.title for m in rows[w.id][:2] if m.title not in titles]
        tiles = [m for w in WORLDS for m in rows[w.id][:4]]
        return {"worlds": list(WORLDS), "rows": rows, "tiles": tiles, "titles": titles}

    return app
