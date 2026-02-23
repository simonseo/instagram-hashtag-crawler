from __future__ import annotations

from pathlib import Path


def file_to_list(filepath: str | Path) -> list[str]:
    """Read a file and return non-empty lines as a list of strings."""
    path = Path(filepath)
    lines = path.read_text().splitlines()
    return [line.strip() for line in lines if line.strip()]
