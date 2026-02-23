from __future__ import annotations

import dataclasses
import json
import logging
from datetime import datetime
from pathlib import Path
from time import sleep
from typing import Any

import instaloader
from instaloader import Hashtag, Post, Profile

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class CrawlConfig:
    """Configuration for a hashtag crawl."""

    output_dir: Path
    min_posts: int = 1
    max_posts: int = 100
    min_timestamp: datetime | None = None


def _collect_posts(
    loader: instaloader.Instaloader,
    hashtag: str,
    config: CrawlConfig,
    profile_cache: dict[int, Profile] | None = None,
    *,
    required_tags: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    """Collect posts from a single hashtag, returning them as a list.

    If *required_tags* is given, only posts whose caption contains **all**
    of the specified hashtags (case-insensitive, without ``#``) are kept.
    This enables efficient AND filtering: query one hashtag via the API
    and check the caption for the remaining tags.

    Posts are deduplicated by shortcode within a single call.
    """
    if profile_cache is None:
        profile_cache = {}

    hashtag_obj = Hashtag.from_name(loader.context, hashtag)
    logger.info("Hashtag #%s has %d total posts", hashtag, hashtag_obj.mediacount)

    posts: list[dict[str, Any]] = []
    seen_shortcodes: set[str] = set()
    skipped = 0

    for post in hashtag_obj.get_posts_resumable():
        if len(posts) >= config.max_posts:
            break

        # Skip if older than min_timestamp
        if config.min_timestamp and post.date_utc < config.min_timestamp:
            if config.min_timestamp is not None:
                # When filtering by time, stop iterating once we hit old posts
                # (posts are returned newest-first)
                break
            continue

        # Only collect single-image posts
        if post.typename != "GraphImage":
            skipped += 1
            continue

        # Deduplicate by shortcode
        if post.shortcode in seen_shortcodes:
            continue
        seen_shortcodes.add(post.shortcode)

        # AND filter: check caption contains all required tags
        if required_tags is not None:
            caption_tags = frozenset(post.caption_hashtags)  # lowercase, no #
            if not required_tags <= caption_tags:
                skipped += 1
                continue

        processed = _process_post(loader, post, profile_cache)
        if processed is not None:
            posts.append(processed)
            if len(posts) % 10 == 0:
                logger.info("Collected %d posts so far...", len(posts))

    logger.info(
        "Collected %d posts for #%s (skipped %d)",
        len(posts),
        hashtag,
        skipped,
    )
    return posts


def crawl(
    loader: instaloader.Instaloader,
    hashtag: str,
    config: CrawlConfig,
) -> bool:
    """Crawl a single hashtag and save results as JSON.

    Returns True if enough posts were collected, False otherwise.
    """
    posts = _collect_posts(loader, hashtag, config)

    if len(posts) < config.min_posts:
        return False

    _save_posts(posts, config.output_dir / f"{hashtag}.json")
    return True


def crawl_multi_and(
    loader: instaloader.Instaloader,
    hashtags: list[str],
    config: CrawlConfig,
) -> bool:
    """Crawl posts that contain ALL given hashtags (AND logic).

    Strategy: query each hashtag via the API and keep only posts whose
    caption contains **every** tag in *hashtags*.  We start with all
    hashtags because Instagram's API returns different post sets for
    each hashtag — a post tagged with both ``#food`` and ``#pizza``
    may appear in the ``#pizza`` feed but be buried far down in the
    ``#food`` feed.  By querying each hashtag and filtering the caption,
    we maximise the chance of finding matching posts.

    Duplicate posts (same shortcode) across queries are merged so the
    final output contains unique posts only.

    Returns True if at least *config.min_posts* were found.
    """
    if len(hashtags) < 2:
        msg = "crawl_multi_and requires at least 2 hashtags"
        raise ValueError(msg)

    required_tags = frozenset(tag.lower() for tag in hashtags)
    profile_cache: dict[int, Profile] = {}
    merged: dict[str, dict[str, Any]] = {}

    for hashtag in hashtags:
        logger.info("AND search: querying #%s (require all of %s)", hashtag, sorted(required_tags))
        posts = _collect_posts(
            loader,
            hashtag,
            config,
            profile_cache,
            required_tags=required_tags,
        )
        for post in posts:
            merged.setdefault(post["shortcode"], post)

        if len(merged) >= config.max_posts:
            break

    all_posts = list(merged.values())[: config.max_posts]

    logger.info(
        "AND search for %s: found %d unique posts",
        " + ".join(f"#{h}" for h in hashtags),
        len(all_posts),
    )

    if len(all_posts) < config.min_posts:
        return False

    filename = "_AND_".join(sorted(hashtags)) + ".json"
    _save_posts(all_posts, config.output_dir / filename)
    return True


def _save_posts(posts: list[dict[str, Any]], output_file: Path) -> None:
    """Write posts to a JSON file."""
    output = {"posts": posts}
    output_file.write_text(json.dumps(output, indent=2, default=str))
    logger.info("Saved %d posts to %s", len(posts), output_file)


def _process_post(
    loader: instaloader.Instaloader,
    post: Post,
    profile_cache: dict[int, Profile],
) -> dict[str, Any] | None:
    """Extract metadata from a single post.

    Returns a dict of post data, or None on failure.
    """
    try:
        profile = _get_profile(loader, post, profile_cache)

        return {
            "shortcode": post.shortcode,
            "user_id": post.owner_id,
            "username": profile.username,
            "full_name": profile.full_name,
            "profile_pic_url": profile.profile_pic_url,
            "media_count": profile.mediacount,
            "follower_count": profile.followers,
            "following_count": profile.followees,
            "date": int(post.date_utc.timestamp()),
            "pic_url": post.url,
            "like_count": post.likes,
            "comment_count": post.comments,
            "caption": post.caption or "",
            "tags": [f"#{tag}" for tag in post.caption_hashtags],
        }
    except instaloader.QueryReturnedNotFoundException:
        logger.warning("Post %s or its owner no longer exists", post.shortcode)
        return None
    except instaloader.ConnectionException as exc:
        logger.warning("Connection error processing post %s: %s", post.shortcode, exc)
        return None


def _get_profile(
    loader: instaloader.Instaloader,
    post: Post,
    cache: dict[int, Profile],
) -> Profile:
    """Fetch owner profile with caching and retry."""
    owner_id = post.owner_id

    if owner_id in cache:
        return cache[owner_id]

    max_retries = 3
    for attempt in range(max_retries):
        try:
            sleep(0.05)  # Small delay to avoid rate limiting
            profile = post.owner_profile
            cache[owner_id] = profile
            return profile
        except instaloader.ConnectionException as exc:
            if attempt < max_retries - 1:
                wait = 5 * (attempt + 1)
                logger.warning(
                    "Rate limited fetching profile for %s, waiting %ds: %s",
                    post.owner_username,
                    wait,
                    exc,
                )
                sleep(wait)
            else:
                raise
    # Unreachable, but satisfies type checker
    msg = "Failed to fetch profile after retries"
    raise RuntimeError(msg)
