from __future__ import annotations

import csv
import json
from pathlib import Path

from instagram_hashtag_crawler.export import RECENCY_THRESHOLD, read_profiles


def _make_post(
    date: int,
    username: str = "user1",
    like_count: int = 10,
) -> dict:
    return {
        "user_id": 123,
        "username": username,
        "full_name": "Test User",
        "profile_pic_url": "https://example.com/pic.jpg",
        "media_count": 50,
        "follower_count": 100,
        "following_count": 50,
        "date": date,
        "pic_url": "https://example.com/post.jpg",
        "like_count": like_count,
        "comment_count": 5,
        "caption": "hello world",
        "tags": ["#test"],
    }


def _read_csv(path: Path) -> list[list[str]]:
    with path.open(newline="") as f:
        return list(csv.reader(f))


def test_read_profiles_basic(tmp_path: Path) -> None:
    """Writes posts to CSV, skipping recent ones."""
    json_dir = tmp_path / "json"
    csv_dir = tmp_path / "csv"
    json_dir.mkdir()

    now = 1_700_000_000
    old_post = _make_post(date=now - RECENCY_THRESHOLD - 1, username="old_user")
    recent_post = _make_post(date=now, username="recent_user")

    data = {"posts": [recent_post, old_post]}
    (json_dir / "food.json").write_text(json.dumps(data))

    read_profiles(json_dir, csv_dir)

    rows = _read_csv(csv_dir / "posts.csv")
    assert len(rows) == 1
    assert rows[0][2] == "old_user"  # username column


def test_read_profiles_empty_json(tmp_path: Path) -> None:
    """An empty posts list produces an empty CSV."""
    json_dir = tmp_path / "json"
    csv_dir = tmp_path / "csv"
    json_dir.mkdir()

    (json_dir / "empty.json").write_text(json.dumps({"posts": []}))

    read_profiles(json_dir, csv_dir)

    rows = _read_csv(csv_dir / "posts.csv")
    assert rows == []


def test_read_profiles_skips_rawfeed(tmp_path: Path) -> None:
    """Files ending in _rawfeed.json are ignored."""
    json_dir = tmp_path / "json"
    csv_dir = tmp_path / "csv"
    json_dir.mkdir()

    now = 1_700_000_000
    post = _make_post(date=now - RECENCY_THRESHOLD - 100)
    (json_dir / "food_rawfeed.json").write_text(json.dumps({"posts": [post]}))

    read_profiles(json_dir, csv_dir)

    rows = _read_csv(csv_dir / "posts.csv")
    assert rows == []


def test_read_profiles_missing_dir(tmp_path: Path) -> None:
    """Raises FileNotFoundError when JSON dir doesn't exist."""
    import pytest

    with pytest.raises(FileNotFoundError):
        read_profiles(tmp_path / "nonexistent", tmp_path / "csv")


def test_read_profiles_multiple_files(tmp_path: Path) -> None:
    """Processes multiple JSON files in sorted order."""
    json_dir = tmp_path / "json"
    csv_dir = tmp_path / "csv"
    json_dir.mkdir()

    now = 1_700_000_000
    old_date = now - RECENCY_THRESHOLD - 100
    for name in ("beta", "alpha"):
        data = {
            "posts": [
                _make_post(date=now, username="recent"),
                _make_post(date=old_date, username=f"{name}_user"),
            ]
        }
        (json_dir / f"{name}.json").write_text(json.dumps(data))

    read_profiles(json_dir, csv_dir)

    rows = _read_csv(csv_dir / "posts.csv")
    assert len(rows) == 2
    # alpha.json sorts before beta.json
    assert rows[0][2] == "alpha_user"
    assert rows[1][2] == "beta_user"
