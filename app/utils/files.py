"""Small filesystem helpers shared by the UI and the core."""

from __future__ import annotations
from pathlib import Path


def unique_path(path: Path) -> Path:
    """Return `path`, or `name (2).ext`, `name (3).ext`... if it already exists,
    so copying results into a folder never overwrites an existing file."""
    if not path.exists():
        return path
    n = 2
    while True:
        candidate = path.with_name(f"{path.stem} ({n}){path.suffix}")
        if not candidate.exists():
            return candidate
        n += 1
