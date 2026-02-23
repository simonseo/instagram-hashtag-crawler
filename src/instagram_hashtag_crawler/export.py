from __future__ import annotations

import argparse
import csv
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Posts within this window (in seconds) from the most recent post are skipped
# to avoid collecting posts that are still accumulating engagement.
RECENCY_THRESHOLD = 60 * 60 * 24  # 24 hours


def read_profiles(
    json_dir: Path,
    csv_dir: Path,
    output_file_name: str = "posts.csv",
) -> None:
    """Read all JSON files in a directory and write post data to CSV."""
    json_dir = Path(json_dir)
    csv_dir = Path(csv_dir)

    if not json_dir.exists():
        msg = f"JSON directory does not exist: {json_dir}"
        raise FileNotFoundError(msg)

    csv_dir.mkdir(parents=True, exist_ok=True)
    output_path = csv_dir / output_file_name

    logger.info("Reading profiles from %s", json_dir)

    with output_path.open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")

        for json_file in sorted(json_dir.iterdir()):
            if json_file.suffix != ".json" or json_file.name.endswith("_rawfeed.json"):
                continue

            logger.debug("Processing %s", json_file.name)
            data = json.loads(json_file.read_text())
            _write_posts(data, writer)

    logger.info("Wrote CSV to %s", output_path)


def _write_posts(data: dict[str, Any], writer: csv.writer) -> None:
    """Write posts from a single JSON file to the CSV writer.

    Posts within the recency threshold of the most recent post are skipped.
    """
    posts: list[dict[str, Any]] = data.get("posts", [])

    if not posts:
        return

    max_date = max(p["date"] for p in posts)
    threshold_date = max_date - RECENCY_THRESHOLD

    for post in posts:
        if post["date"] > threshold_date:
            continue

        row = [
            post.get("shortcode", ""),
            str(post.get("pic_url", "")),
            post.get("like_count", 0),
            post.get("username", ""),
            post.get("user_id", ""),
            post.get("full_name", ""),
            post.get("profile_pic_url", ""),
            post.get("media_count", 0),
            post.get("follower_count", 0),
            post.get("comment_count", 0),
            post.get("date", 0),
            str(post.get("caption", "")),
            post.get("tags", []),
        ]
        writer.writerow(row)


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint for exporting JSON data to CSV."""
    parser = argparse.ArgumentParser(
        prog="instagram-hashtag-export",
        description="Export crawled hashtag data from JSON to CSV.",
    )
    parser.add_argument(
        "--json-dir",
        required=True,
        help="Directory containing crawled JSON files",
    )
    parser.add_argument(
        "--csv-dir",
        required=True,
        help="Directory to write CSV output",
    )
    parser.add_argument(
        "--output-file",
        default="posts.csv",
        help="Output CSV filename (default: posts.csv)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")

    args = parser.parse_args(argv)

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    read_profiles(
        json_dir=Path(args.json_dir),
        csv_dir=Path(args.csv_dir),
        output_file_name=args.output_file,
    )
