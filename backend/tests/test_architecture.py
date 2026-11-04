"""The layers of the backend only depend downwards (see ARCHITECTURE.md). A new import across the rule fails here."""

import re
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1] / "cinesense"

# role -> the roles it may import from
ALLOWED = {
    "core": set(),
    "data_sources": {"core"},
    "search": {"core"},
    "taste": {"core"},
    "catalog_import": {"core", "data_sources"},
    "chat_agent": {"core", "search", "taste"},
    "web_api": {"core", "data_sources", "search", "taste", "chat_agent", "catalog_import"},
    "evaluation": {"core", "data_sources", "search", "taste", "chat_agent", "web_api"},
}
_IMPORT = re.compile(r"^\s*(?:from|import) cinesense\.([a-z_]+)", re.M)


def imports_of(role: str) -> dict[str, set[str]]:
    """Other roles each module of this role imports, by module path."""
    found = {}
    for path in (PACKAGE / role).rglob("*.py"):
        used = {m for m in _IMPORT.findall(path.read_text()) if m != role}
        if used:
            found[str(path.relative_to(PACKAGE))] = used
    return found


def test_every_role_is_listed():
    roles = {p.name for p in PACKAGE.iterdir() if p.is_dir() and (p / "__init__.py").exists()}
    assert roles == set(ALLOWED)


@pytest.mark.parametrize("role", sorted(ALLOWED))
def test_role_imports_only_lower_layers(role):
    bad = {path: used - ALLOWED[role] for path, used in imports_of(role).items() if used - ALLOWED[role]}
    assert not bad, f"{role} may only import {sorted(ALLOWED[role]) or 'nothing'}: {bad}"
