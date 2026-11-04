"""How well a film fits the requested mood tags.

tag_match is CineSense's weighted mean of the requested tags; tag_scores is movieFinder's cosine (a baseline)."""

import numpy as np


def tag_scores(weights: dict[int, int], matrix: np.ndarray) -> np.ndarray:
    """movieFinder baseline: cosine of a weighted one-hot tag vector with each row; zeros if no weights."""
    n = matrix.shape[0]
    if not weights:
        return np.zeros(n, dtype=np.float32)
    user = np.zeros(matrix.shape[1], dtype=np.float32)
    for idx, w in weights.items():
        user[idx] = w
    m = np.nan_to_num(matrix)
    denom = np.linalg.norm(m, axis=1) * np.linalg.norm(user)
    with np.errstate(divide="ignore", invalid="ignore"):
        sims = np.where(denom > 0, m @ user / denom, 0.0)
    return sims.astype(np.float32)


def tag_match(weights: dict[int, int], matrix: np.ndarray) -> np.ndarray:
    """Weighted mean relevance of the requested tags only (0..1). Unlike cosine over all 1,128 tags it does
    not flatter films with a thin tag profile."""
    if not weights:
        return np.zeros(matrix.shape[0], dtype=np.float32)
    idxs = list(weights)
    w = np.asarray([weights[i] for i in idxs], dtype=np.float32)
    return (np.nan_to_num(matrix[:, idxs]) @ w / w.sum()).astype(np.float32)
