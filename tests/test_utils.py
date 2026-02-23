from __future__ import annotations

from pathlib import Path

from instagram_hashtag_crawler.utils import file_to_list


def test_file_to_list_basic(tmp_path: Path) -> None:
    """Read a file with normal lines."""
    f = tmp_path / "tags.txt"
    f.write_text("alpha\nbeta\ngamma\n")
    result = file_to_list(f)
    assert result == ["alpha", "beta", "gamma"]


def test_file_to_list_skips_blank_lines(tmp_path: Path) -> None:
    """Blank lines and whitespace-only lines are excluded."""
    f = tmp_path / "tags.txt"
    f.write_text("alpha\n\n  \nbeta\n")
    result = file_to_list(f)
    assert result == ["alpha", "beta"]


def test_file_to_list_strips_whitespace(tmp_path: Path) -> None:
    """Leading/trailing whitespace is stripped from each line."""
    f = tmp_path / "tags.txt"
    f.write_text("  alpha  \n\tbeta\t\n")
    result = file_to_list(f)
    assert result == ["alpha", "beta"]


def test_file_to_list_empty_file(tmp_path: Path) -> None:
    """An empty file returns an empty list."""
    f = tmp_path / "empty.txt"
    f.write_text("")
    result = file_to_list(f)
    assert result == []


def test_file_to_list_accepts_string_path(tmp_path: Path) -> None:
    """Accepts a string path, not just Path objects."""
    f = tmp_path / "tags.txt"
    f.write_text("one\ntwo\n")
    result = file_to_list(str(f))
    assert result == ["one", "two"]
