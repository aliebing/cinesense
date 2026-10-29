"""Map free-text mood words from the model or the user onto Tag Genome tags (never invent an index)."""

import difflib

SYNONYMS = {
    "spooky": "creepy",
    "scary film": "scary",
    "middle ages": "medieval",
    "mediaeval": "medieval",
    "space": "space travel",
    "outer space": "space",
    "wwii": "world war ii",
    "ww2": "world war ii",
    "second world war": "world war ii",
    "wwi": "world war i",
    "gory": "gore",
    "bloody": "gore",
    "humorous": "funny",
    "lighthearted": "feel-good",
    "feel good": "feel-good",
    "uplifting": "feel-good",
    "nazi germany": "nazis",
    "german history": "germany",
    "romantic": "romantic",
    "sci-fi": "sci-fi",
    "science fiction": "sci-fi",
}


def resolve_tags(names: list[str], all_tags: list[str]) -> tuple[list[tuple[str, int]], list[str]]:
    index = {t.lower(): i for i, t in enumerate(all_tags)}
    resolved: list[tuple[str, int]] = []
    unresolved: list[str] = []
    for raw in names:
        name = " ".join(raw.lower().strip().split())
        candidate = name if name in index else SYNONYMS.get(name)
        if candidate and candidate.lower() in index:
            i = index[candidate.lower()]
        else:
            close = difflib.get_close_matches(name, list(index), n=1, cutoff=0.8)
            if not close:
                unresolved.append(raw)
                continue
            i = index[close[0]]
        resolved.append((all_tags[i], i))
    return resolved, unresolved
