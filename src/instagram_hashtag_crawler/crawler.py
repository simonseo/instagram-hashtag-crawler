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


def crawl(
    loader: instaloader.Instaloader,
    hashtag: str,
    config: CrawlConfig,
) -> bool:
    """Crawl a single hashtag and save results as JSON.

    Returns True if enough posts were collected, False otherwise.
    """
    hashtag_obj = Hashtag.from_name(loader.context, hashtag)
    logger.info("Hashtag #%s has %d total posts", hashtag, hashtag_obj.mediacount)

    profile_cache: dict[int, Profile] = {}
    posts: list[dict[str, Any]] = []
    skipped = 0

    for post in hashtag_obj.get_posts():
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

        processed = _process_post(loader, post, profile_cache)
        if processed is not None:
            posts.append(processed)
            if len(posts) % 10 == 0:
                logger.info("Collected %d posts so far...", len(posts))

    logger.info(
        "Collected %d posts for #%s (skipped %d non-image)",
        len(posts),
        hashtag,
        skipped,
    )

    if len(posts) < config.min_posts:
        return False

    # Save processed results
    output = {"posts": posts}
    output_file = config.output_dir / f"{hashtag}.json"
    output_file.write_text(json.dumps(output, indent=2, default=str))
    logger.info("Saved %d posts to %s", len(posts), output_file)

    return True


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
    except instaloader.ConnectionException as exc:
        logger.warning("Connection error processing post %s: %s", post.shortcode, exc)
        return None
    except instaloader.QueryReturnedNotFoundException:
        logger.warning("Post %s or its owner no longer exists", post.shortcode)
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
