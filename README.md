# Instagram Hashtag Crawler

Crawl Instagram hashtags and collect post metadata (likes, comments, captions, user profiles) without a developer account.

Uses [instaloader](https://instaloader.github.io/) under the hood.

## Installation

```bash
pip install .
```

For development:

```bash
pip install -e ".[dev]"
```

## Usage

### Crawl hashtags

```bash
# Single hashtag
instagram-hashtag-crawler -u YOUR_USERNAME -p YOUR_PASSWORD -t foodporn

# Multiple hashtags from a file
instagram-hashtag-crawler -u YOUR_USERNAME -p YOUR_PASSWORD -f targets.txt

# With options
instagram-hashtag-crawler -u YOUR_USERNAME -p YOUR_PASSWORD -t foodporn \
    --max-posts 500 \
    --output-dir ./data \
    --session-file session.dat \
    -v
```

### Multi-hashtag AND search

Pass `-t` multiple times to find posts that contain **all** specified hashtags:

```bash
# Posts tagged with BOTH #foodporn AND #pizza
instagram-hashtag-crawler -u YOUR_USERNAME -p YOUR_PASSWORD -t foodporn -t pizza

# Three-way AND
instagram-hashtag-crawler -u YOUR_USERNAME -p YOUR_PASSWORD -t food -t pizza -t italy
```

Output is saved as `food_AND_pizza.json` (tags sorted alphabetically, joined by `_AND_`).

You can also run it as a module:

```bash
python -m instagram_hashtag_crawler -u YOUR_USERNAME -p YOUR_PASSWORD -t foodporn
```

### Export to CSV

```bash
instagram-hashtag-export --json-dir ./hashtags --csv-dir ./output
```

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `-u`, `--username` | Instagram username | (required) |
| `-p`, `--password` | Instagram password | (required) |
| `-t`, `--target` | Hashtag to crawl (without `#`). Repeat for AND search. | — |
| `-f`, `--targetfile` | File with hashtags, one per line | — |
| `--output-dir` | Directory for JSON output | `./hashtags` |
| `--max-posts` | Max posts per hashtag | `100` |
| `--min-posts` | Min posts required | `1` |
| `--since` | Unix timestamp — only collect newer posts | — |
| `--session-file` | Path to save/load session | — |
| `-v`, `--verbose` | Debug logging | off |

### Target file format

One hashtag per line, no `#` prefix:

```
delicious
dish
foodpornography
```

See [`examples/targets.txt`](examples/targets.txt) for a sample.

## Output

Each hashtag produces a JSON file in the output directory:

```
hashtags/
  delicious.json
  dish.json
  food_AND_pizza.json   # multi-hashtag AND result
```

Each JSON file contains an array of post objects with fields like `shortcode`, `user_id`, `username`, `like_count`, `comment_count`, `caption`, `tags`, `pic_url`, `date`, and profile metadata.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Lint
ruff check src/ tests/
ruff format --check src/ tests/

# Test
pytest

# Pre-commit hooks
pre-commit install
```

## Requirements

- Python 3.10+
- An Instagram account (no developer/API access needed)

## License

MIT
