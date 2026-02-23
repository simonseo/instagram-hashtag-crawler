from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from instagram_hashtag_crawler.crawler import (
    CrawlConfig,
    _collect_posts,
    _save_posts,
    crawl,
    crawl_multi_and,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_post(
    shortcode: str,
    caption_hashtags: list[str],
    *,
    typename: str = "GraphImage",
    date_utc: datetime | None = None,
) -> MagicMock:
    """Build a minimal mock instaloader Post."""
    post = MagicMock()
    post.shortcode = shortcode
    post.typename = typename
    post.caption_hashtags = caption_hashtags  # lowercase, no #
    post.caption = " ".join(f"#{t}" for t in caption_hashtags)
    post.date_utc = date_utc or datetime(2025, 1, 1, tzinfo=timezone.utc)
    post.owner_id = hash(shortcode) % 10_000
    post.owner_username = f"user_{shortcode}"
    post.url = f"https://example.com/{shortcode}.jpg"
    post.likes = 42
    post.comments = 7
    return post


def _fake_profile() -> MagicMock:
    profile = MagicMock()
    profile.username = "testuser"
    profile.full_name = "Test User"
    profile.profile_pic_url = "https://example.com/pic.jpg"
    profile.mediacount = 100
    profile.followers = 500
    profile.followees = 200
    return profile


def _fake_hashtag_obj(posts: list[MagicMock], mediacount: int = 999) -> MagicMock:
    ht = MagicMock()
    ht.mediacount = mediacount
    ht.get_posts.return_value = iter(posts)
    return ht


def _make_config(tmp_path: Path, **kwargs: Any) -> CrawlConfig:
    output_dir = tmp_path / "output"
    output_dir.mkdir(exist_ok=True)
    return CrawlConfig(output_dir=output_dir, **kwargs)


# ---------------------------------------------------------------------------
# _collect_posts
# ---------------------------------------------------------------------------


@patch("instagram_hashtag_crawler.crawler._get_profile")
@patch("instagram_hashtag_crawler.crawler.Hashtag")
def test_collect_posts_basic(
    mock_hashtag_cls: MagicMock,
    mock_get_profile: MagicMock,
    tmp_path: Path,
) -> None:
    """Collects posts and includes shortcode in output."""
    mock_get_profile.return_value = _fake_profile()
    posts = [_fake_post("ABC", ["food", "pizza"])]
    mock_hashtag_cls.from_name.return_value = _fake_hashtag_obj(posts)

    config = _make_config(tmp_path)
    loader = MagicMock()
    result = _collect_posts(loader, "food", config)

    assert len(result) == 1
    assert result[0]["shortcode"] == "ABC"
    assert "#food" in result[0]["tags"]


@patch("instagram_hashtag_crawler.crawler._get_profile")
@patch("instagram_hashtag_crawler.crawler.Hashtag")
def test_collect_posts_required_tags_filters(
    mock_hashtag_cls: MagicMock,
    mock_get_profile: MagicMock,
    tmp_path: Path,
) -> None:
    """Only posts whose caption contains ALL required tags are kept."""
    mock_get_profile.return_value = _fake_profile()
    posts = [
        _fake_post("A", ["food", "pizza", "italy"]),  # has both required
        _fake_post("B", ["food"]),  # missing pizza
        _fake_post("C", ["pizza", "food", "cheese"]),  # has both required
    ]
    mock_hashtag_cls.from_name.return_value = _fake_hashtag_obj(posts)

    config = _make_config(tmp_path)
    loader = MagicMock()
    result = _collect_posts(loader, "food", config, required_tags=frozenset({"food", "pizza"}))

    shortcodes = [p["shortcode"] for p in result]
    assert shortcodes == ["A", "C"]


@patch("instagram_hashtag_crawler.crawler._get_profile")
@patch("instagram_hashtag_crawler.crawler.Hashtag")
def test_collect_posts_deduplicates_by_shortcode(
    mock_hashtag_cls: MagicMock,
    mock_get_profile: MagicMock,
    tmp_path: Path,
) -> None:
    """Duplicate shortcodes within one query are skipped."""
    mock_get_profile.return_value = _fake_profile()
    posts = [
        _fake_post("DUP", ["food"]),
        _fake_post("DUP", ["food"]),  # same shortcode
        _fake_post("UNIQUE", ["food"]),
    ]
    mock_hashtag_cls.from_name.return_value = _fake_hashtag_obj(posts)

    config = _make_config(tmp_path)
    loader = MagicMock()
    result = _collect_posts(loader, "food", config)

    shortcodes = [p["shortcode"] for p in result]
    assert shortcodes == ["DUP", "UNIQUE"]


@patch("instagram_hashtag_crawler.crawler._get_profile")
@patch("instagram_hashtag_crawler.crawler.Hashtag")
def test_collect_posts_skips_non_image(
    mock_hashtag_cls: MagicMock,
    mock_get_profile: MagicMock,
    tmp_path: Path,
) -> None:
    """Non-GraphImage posts are skipped."""
    mock_get_profile.return_value = _fake_profile()
    posts = [
        _fake_post("VID", ["food"], typename="GraphVideo"),
        _fake_post("IMG", ["food"]),
    ]
    mock_hashtag_cls.from_name.return_value = _fake_hashtag_obj(posts)

    config = _make_config(tmp_path)
    loader = MagicMock()
    result = _collect_posts(loader, "food", config)

    assert len(result) == 1
    assert result[0]["shortcode"] == "IMG"


@patch("instagram_hashtag_crawler.crawler._get_profile")
@patch("instagram_hashtag_crawler.crawler.Hashtag")
def test_collect_posts_respects_max_posts(
    mock_hashtag_cls: MagicMock,
    mock_get_profile: MagicMock,
    tmp_path: Path,
) -> None:
    """Stops collecting after max_posts."""
    mock_get_profile.return_value = _fake_profile()
    posts = [_fake_post(f"P{i}", ["food"]) for i in range(10)]
    mock_hashtag_cls.from_name.return_value = _fake_hashtag_obj(posts)

    config = _make_config(tmp_path, max_posts=3)
    loader = MagicMock()
    result = _collect_posts(loader, "food", config)

    assert len(result) == 3


# ---------------------------------------------------------------------------
# crawl (single hashtag — refactored to use _collect_posts)
# ---------------------------------------------------------------------------


@patch("instagram_hashtag_crawler.crawler._get_profile")
@patch("instagram_hashtag_crawler.crawler.Hashtag")
def test_crawl_single_writes_json(
    mock_hashtag_cls: MagicMock,
    mock_get_profile: MagicMock,
    tmp_path: Path,
) -> None:
    """Single-hashtag crawl writes {hashtag}.json with shortcode field."""
    mock_get_profile.return_value = _fake_profile()
    posts = [_fake_post("XYZ", ["travel"])]
    mock_hashtag_cls.from_name.return_value = _fake_hashtag_obj(posts)

    config = _make_config(tmp_path)
    loader = MagicMock()
    result = crawl(loader, "travel", config)

    assert result is True
    output_file = config.output_dir / "travel.json"
    assert output_file.exists()
    data = json.loads(output_file.read_text())
    assert len(data["posts"]) == 1
    assert data["posts"][0]["shortcode"] == "XYZ"


@patch("instagram_hashtag_crawler.crawler._get_profile")
@patch("instagram_hashtag_crawler.crawler.Hashtag")
def test_crawl_single_returns_false_below_min(
    mock_hashtag_cls: MagicMock,
    mock_get_profile: MagicMock,
    tmp_path: Path,
) -> None:
    """Returns False when fewer than min_posts collected."""
    mock_get_profile.return_value = _fake_profile()
    mock_hashtag_cls.from_name.return_value = _fake_hashtag_obj([])

    config = _make_config(tmp_path, min_posts=5)
    loader = MagicMock()
    result = crawl(loader, "empty", config)

    assert result is False


# ---------------------------------------------------------------------------
# crawl_multi_and
# ---------------------------------------------------------------------------


@patch("instagram_hashtag_crawler.crawler._get_profile")
@patch("instagram_hashtag_crawler.crawler.Hashtag")
def test_crawl_multi_and_intersection(
    mock_hashtag_cls: MagicMock,
    mock_get_profile: MagicMock,
    tmp_path: Path,
) -> None:
    """AND search keeps only posts containing all requested hashtags."""
    mock_get_profile.return_value = _fake_profile()

    # Simulate two hashtag feeds
    food_posts = [
        _fake_post("A", ["food", "pizza"]),  # matches both
        _fake_post("B", ["food"]),  # missing pizza
    ]
    pizza_posts = [
        _fake_post("A", ["food", "pizza"]),  # same post, will be deduped
        _fake_post("C", ["pizza", "food"]),  # matches both
        _fake_post("D", ["pizza"]),  # missing food
    ]

    call_count = 0

    def from_name_side_effect(_ctx: Any, name: str) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if name == "food":
            return _fake_hashtag_obj(food_posts)
        return _fake_hashtag_obj(pizza_posts)

    mock_hashtag_cls.from_name.side_effect = from_name_side_effect

    config = _make_config(tmp_path)
    loader = MagicMock()
    result = crawl_multi_and(loader, ["food", "pizza"], config)

    assert result is True

    # Output file: sorted hashtags joined by _AND_
    output_file = config.output_dir / "food_AND_pizza.json"
    assert output_file.exists()
    data = json.loads(output_file.read_text())

    shortcodes = {p["shortcode"] for p in data["posts"]}
    assert "A" in shortcodes  # found in both feeds
    assert "C" in shortcodes  # found in pizza feed, has both tags
    assert "B" not in shortcodes  # only has food
    assert "D" not in shortcodes  # only has pizza


def test_crawl_multi_and_requires_two_hashtags(tmp_path: Path) -> None:
    """Raises ValueError if fewer than 2 hashtags."""
    config = _make_config(tmp_path)
    loader = MagicMock()
    with pytest.raises(ValueError, match="at least 2 hashtags"):
        crawl_multi_and(loader, ["solo"], config)


@patch("instagram_hashtag_crawler.crawler._get_profile")
@patch("instagram_hashtag_crawler.crawler.Hashtag")
def test_crawl_multi_and_returns_false_below_min(
    mock_hashtag_cls: MagicMock,
    mock_get_profile: MagicMock,
    tmp_path: Path,
) -> None:
    """Returns False when no posts match all tags."""
    mock_get_profile.return_value = _fake_profile()

    # No posts have both tags
    mock_hashtag_cls.from_name.return_value = _fake_hashtag_obj(
        [
            _fake_post("X", ["food"]),
        ]
    )

    config = _make_config(tmp_path, min_posts=1)
    loader = MagicMock()
    result = crawl_multi_and(loader, ["food", "pizza"], config)

    assert result is False


@patch("instagram_hashtag_crawler.crawler._get_profile")
@patch("instagram_hashtag_crawler.crawler.Hashtag")
def test_crawl_multi_and_deduplicates_across_feeds(
    mock_hashtag_cls: MagicMock,
    mock_get_profile: MagicMock,
    tmp_path: Path,
) -> None:
    """Same post appearing in multiple feeds is only included once."""
    mock_get_profile.return_value = _fake_profile()

    shared_post = _fake_post("SHARED", ["food", "pizza"])
    feed1 = [shared_post]
    feed2 = [shared_post]

    call_count = 0

    def from_name_side_effect(_ctx: Any, name: str) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _fake_hashtag_obj(feed1)
        return _fake_hashtag_obj(feed2)

    mock_hashtag_cls.from_name.side_effect = from_name_side_effect

    config = _make_config(tmp_path)
    loader = MagicMock()
    crawl_multi_and(loader, ["food", "pizza"], config)

    output_file = config.output_dir / "food_AND_pizza.json"
    data = json.loads(output_file.read_text())

    assert len(data["posts"]) == 1
    assert data["posts"][0]["shortcode"] == "SHARED"


# ---------------------------------------------------------------------------
# _save_posts
# ---------------------------------------------------------------------------


def test_save_posts_writes_json(tmp_path: Path) -> None:
    """_save_posts writes valid JSON with posts key."""
    posts = [{"shortcode": "A", "user_id": 1}]
    output_file = tmp_path / "test.json"
    _save_posts(posts, output_file)

    data = json.loads(output_file.read_text())
    assert data == {"posts": [{"shortcode": "A", "user_id": 1}]}
