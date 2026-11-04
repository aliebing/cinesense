"""Input sanitising, a prompt-injection heuristic and a prompt-leak check for the chat agent.

Deliberately simple and deterministic: a few patterns for the common attacks in English and German. A message
that matches never reaches the model; a reply that quotes the system prompt is replaced. Film wishes about AIs
("an AI that pretends to be human") must pass, so the patterns target instructions to the assistant itself.
"""

from __future__ import annotations

import re

GUARD_REPLY = "I can only help you find films. Tell me a mood, a story or a film you like."

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_ZERO_WIDTH = re.compile("[​-‍⁠﻿]")
_INLINE_SPACE = re.compile(r"[ \t]+")
_WS = re.compile(r"\s+")

_ADJ = r"(?:all|any|the|your|my|these|those|previous|prior|above|earlier)"
_DE_ADJ = r"(?:alle|alles|die|deine|diese|jegliche|vorherigen|vorigen|bisherigen|obigen|bisherige)"
_ROLE_EN = r"(?:assistant|ai|dan|model|bot|chatbot|unrestricted|jailbroken|evil)"
_ROLE_DE = r"(?:assistent\w*|ki|dan|modell|bot|chatbot|uneingeschr\w+|ohne regeln)"
_INJECTION = [
    re.compile(p, re.IGNORECASE)
    for p in (
        rf"\b(?:ignore|disregard|forget)\s+(?:{_ADJ}\s+)+(?:instructions|prompts|rules)\b",
        r"\b(?:reveal|print|show|repeat)(?: me)? (?:your (?:system )?|the system )(?:prompt|instructions)\b",
        r"\bsystem[ -]?prompt\b",
        r"\bapi[ _-]?(?:key|schlüssel|schluessel)\b",
        rf"\byou are now (?:an? |the )?(?:\w+ ){{0,2}}?{_ROLE_EN}\b",
        r"\bpretend (?:to be|you are) (?:an? )?(?:\w+ ){0,2}?(?:unrestricted|jailbroken|without rules)",
        # the graph's own note to the model (graph.agent) must not be forgeable by the user
        r"\[\s*cinesense system note\s*\]",
        # German
        rf"\b(?:ignorier\w*|vergiss|missachte\w*)\s+(?:{_DE_ADJ}\s+)+(?:anweisungen|instruktionen|regeln|befehle)\b",
        (
            r"\b(?:zeig|zeige|verrate|wiederhole|nenne|gib)(?: mir)? (?:deinen|deine|dein) "
            r"(?:system[ -]?prompt|anweisungen|instruktionen)\b"
        ),
        rf"\bdu bist (?:jetzt|nun|ab jetzt) (?:ein |eine |der |die )?(?:\w+ ){{0,2}}?{_ROLE_DE}",
    )
]


def sanitize(text: str) -> str:
    """Drops control and zero-width characters (which can hide an attack from the patterns) and extra spaces."""
    return _INLINE_SPACE.sub(" ", _CONTROL.sub("", _ZERO_WIDTH.sub("", text))).strip()


def looks_like_injection(text: str) -> bool:
    return any(p.search(text) for p in _INJECTION)


def leaks_prompt(answer: str, prompts: list[str], min_overlap: int = 60) -> bool:
    """True if the answer contains min_overlap consecutive characters of one of the prompts."""
    ans = _WS.sub(" ", answer)
    for prompt in prompts:
        sp = _WS.sub(" ", prompt).strip()
        if sp and any(sp[i : i + min_overlap] in ans for i in range(max(1, len(sp) - min_overlap + 1))):
            return True
    return False
