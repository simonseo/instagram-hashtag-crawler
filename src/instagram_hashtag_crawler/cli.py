from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import instaloader

from instagram_hashtag_crawler.crawler import CrawlConfig, crawl
from instagram_hashtag_crawler.utils import file_to_list

logger = logging.getLogger(__name__)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="instagram-hashtag-crawler",
        description="Crawl Instagram hashtags and collect post metadata.",
    )
    parser.add_argument("-u", "--username", required=True, help="Instagram username")
    parser.add_argument("-p", "--password", required=True, help="Instagram password")
    parser.add_argument("-t", "--target", help="Single hashtag to crawl (without #)")
    parser.add_argument("-f", "--targetfile", help="Path to file with hashtags (one per line)")
    parser.add_argument(
        "--output-dir",
        default="./hashtags",
        help="Directory for output data (default: ./hashtags)",
    )
    parser.add_argument(
        "--max-posts",
        type=int,
        default=100,
        help="Maximum posts to collect per hashtag (default: 100)",
    )
    parser.add_argument(
        "--min-posts",
        type=int,
        default=1,
        help="Minimum posts required per hashtag (default: 1)",
    )
    parser.add_argument(
        "--since",
        type=int,
        default=None,
        help="Unix timestamp — only collect posts newer than this",
    )
    parser.add_argument(
        "--session-file",
        default=None,
        help="Path to save/load login session file",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _login(
    loader: instaloader.Instaloader,
    username: str,
    password: str,
    session_file: str | None,
) -> None:
    """Attempt session restore, fall back to username/password login."""
    if session_file:
        try:
            loader.load_session_from_file(username, filename=session_file)
            if loader.test_login() == username:
                logger.info("Restored session from %s", session_file)
                return
        except FileNotFoundError:
            logger.debug("No session file at %s, will login fresh", session_file)

    # Try default session location
    try:
        loader.load_session_from_file(username)
        if loader.test_login() == username:
            logger.info("Restored session for %s", username)
            return
    except FileNotFoundError:
        logger.debug("No default session file found")

    logger.info("Logging in as %s", username)
    loader.login(username, password)

    # Save session for next time
    if session_file:
        loader.save_session_to_file(filename=session_file)
    else:
        loader.save_session_to_file()
    logger.info("Session saved")


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    _setup_logging(args.verbose)

    # Resolve targets
    if args.target:
        hashtags = [args.target]
    elif args.targetfile:
        hashtags = file_to_list(args.targetfile)
    else:
        logger.error("Provide a hashtag with -t or a file of hashtags with -f")
        sys.exit(1)

    logger.info("Targets: %s", hashtags)

    # Initialize instaloader and login
    loader = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
    )

    try:
        _login(loader, args.username, args.password, args.session_file)
    except instaloader.InvalidArgumentException as exc:
        logger.error("Login failed: %s", exc)
        sys.exit(1)
    except instaloader.TwoFactorAuthRequiredException:
        logger.error(
            "Two-factor auth required. Use --session-file with a pre-authenticated session."
        )
        sys.exit(1)

    # Build config
    from datetime import datetime, timezone

    min_ts = None
    if args.since is not None:
        min_ts = datetime.fromtimestamp(args.since, tz=timezone.utc)

    config = CrawlConfig(
        output_dir=Path(args.output_dir),
        min_posts=args.min_posts,
        max_posts=args.max_posts,
        min_timestamp=min_ts,
    )

    config.output_dir.mkdir(parents=True, exist_ok=True)

    # Crawl each hashtag
    for hashtag in hashtags:
        logger.info("Crawling #%s", hashtag)
        try:
            success = crawl(loader, hashtag, config)
            if success:
                logger.info("Finished #%s", hashtag)
            else:
                logger.warning("Insufficient posts for #%s", hashtag)
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            sys.exit(130)
        except instaloader.QueryReturnedNotFoundException:
            logger.warning("Hashtag #%s not found, skipping", hashtag)
