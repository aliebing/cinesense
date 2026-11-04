"""Long-term taste profile from 👍/👎: what the liked films have more of than the average film
(disliked films count against), reduced to a few weighted Tag Genome tags."""

import numpy as np
from pydantic import BaseModel, Field

TASTE_TAGS = 8
MIN_LIFT = 0.15  # a tag must be clearly above the catalogue average to count as taste
DISLIKE_FACTOR = 0.5


class Profile(BaseModel):
    liked: list[str] = Field(default_factory=list)
    disliked: list[str] = Field(default_factory=list)
    taste: dict[int, int] = Field(default_factory=dict)  # tag idx -> weight 1..10
    taste_names: list[str] = Field(default_factory=list)  # strongest first

    @classmethod
    def empty(cls) -> "Profile":
        return cls()

    def is_empty(self) -> bool:
        return not (self.liked or self.disliked)


def build_profile(feedback: dict[str, int], provider) -> Profile:
    liked = [f for f, v in feedback.items() if v > 0]
    disliked = [f for f, v in feedback.items() if v < 0]
    if not liked:
        return Profile(liked=liked, disliked=disliked)
    mean = provider.mean_tag_vector()

    def avg(ids: list[str]) -> np.ndarray | None:
        if not ids:
            return None
        vecs = provider.tag_vectors(ids)
        vecs = vecs[~np.isnan(vecs).any(axis=1)]
        return vecs.mean(axis=0) if len(vecs) else None

    like_vec = avg(liked)
    if like_vec is None:  # only films without a Tag Genome vector (live imports)
        return Profile(liked=liked, disliked=disliked)
    lift = like_vec - mean
    if (dislike_vec := avg(disliked)) is not None:
        lift -= DISLIKE_FACTOR * np.clip(dislike_vec - mean, 0, None)
    top = [int(i) for i in np.argsort(-lift)[:TASTE_TAGS] if lift[i] >= MIN_LIFT]
    if not top:
        return Profile(liked=liked, disliked=disliked)
    best = float(lift[top[0]])
    taste = {i: max(1, round(10 * float(lift[i]) / best)) for i in top}
    names = provider.list_tags()
    return Profile(liked=liked, disliked=disliked, taste=taste, taste_names=[names[i] for i in top])
