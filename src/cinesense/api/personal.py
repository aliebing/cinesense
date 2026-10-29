"""Anonymous personalisation: 👍/👎 per browser id (header X-CineSense-User) and the derived taste profile."""

import re
import threading
from collections import OrderedDict
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from cinesense.api.deps import get_feedback_store, get_provider
from cinesense.personal.profile import Profile, build_profile

_USER_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")
router = APIRouter()


def get_user(x_cinesense_user: Annotated[str | None, Header()] = None) -> str | None:
    """A random id from the browser; anything else is ignored (unpersonalised)."""
    return x_cinesense_user if x_cinesense_user and _USER_ID.match(x_cinesense_user) else None


def get_user_profile(
    user: Annotated[str | None, Depends(get_user)],
    store: Annotated[object, Depends(get_feedback_store)],
    provider: Annotated[object, Depends(get_provider)],
) -> Profile | None:
    if user is None:
        return None
    feedback = store.get(user)
    return cached_profile(feedback, provider) if feedback else None


_CACHE_SIZE = 512
_profiles: OrderedDict[tuple, Profile] = OrderedDict()
_profiles_lock = threading.Lock()


def cached_profile(feedback: dict[str, int], provider) -> Profile:
    """Profiles depend only on the feedback, so they are cached by its content (no invalidation needed)."""
    key = (id(provider), tuple(sorted(feedback.items())))
    with _profiles_lock:
        if key in _profiles:
            _profiles.move_to_end(key)
            return _profiles[key]
    prof = build_profile(feedback, provider)
    with _profiles_lock:
        _profiles[key] = prof
        while len(_profiles) > _CACHE_SIZE:
            _profiles.popitem(last=False)
    return prof


UserProfile = Annotated[Profile | None, Depends(get_user_profile)]


class FeedbackRequest(BaseModel):
    film_id: str = Field(min_length=1, max_length=80)
    value: Literal[-1, 0, 1]


class FilmRef(BaseModel):
    id: str
    title: str
    year: int | None = None


class ProfileSummary(BaseModel):
    liked: list[FilmRef] = Field(default_factory=list)
    disliked: list[FilmRef] = Field(default_factory=list)
    taste: list[str] = Field(default_factory=list)


def summary(profile: Profile | None, provider) -> ProfileSummary:
    if profile is None:
        return ProfileSummary()
    films = {m.id: m for m in provider.get_many(profile.liked + profile.disliked)}

    def refs(ids: list[str]) -> list[FilmRef]:
        return [FilmRef(id=i, title=films[i].title, year=films[i].year) for i in ids if i in films]

    return ProfileSummary(liked=refs(profile.liked), disliked=refs(profile.disliked), taste=profile.taste_names)


@router.post("/api/feedback")
def feedback(
    req: FeedbackRequest,
    user: Annotated[str | None, Depends(get_user)],
    store: Annotated[object, Depends(get_feedback_store)],
    provider: Annotated[object, Depends(get_provider)],
) -> ProfileSummary:
    if user is None:
        raise HTTPException(status_code=400, detail="missing_user_id")
    store.set(user, req.film_id, req.value)
    fb = store.get(user)
    return summary(cached_profile(fb, provider) if fb else None, provider)


@router.get("/api/profile")
def profile(profile: UserProfile, provider: Annotated[object, Depends(get_provider)]) -> ProfileSummary:
    return summary(profile, provider)


@router.delete("/api/profile")
def reset(
    user: Annotated[str | None, Depends(get_user)], store: Annotated[object, Depends(get_feedback_store)]
) -> ProfileSummary:
    if user is not None:
        store.clear(user)
    return ProfileSummary()
