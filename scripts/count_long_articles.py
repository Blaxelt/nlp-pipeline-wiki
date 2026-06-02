import argparse
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

parser = argparse.ArgumentParser(
    description="Count articles exceeding a character threshold"
)
parser.add_argument("--date", default="20260301", help="Dump date (default: 20260301)")
parser.add_argument(
    "--threshold",
    type=int,
    default=1_000_000,
    help="Character threshold (default: 1000000)",
)
args = parser.parse_args()

data_path = (
    DATA_DIR
    / f"eswiki-{args.date}-pages-articles-ns0-no-redirects-clean.json"
)

if not data_path.exists():
    print(f"Error: Dump not found at {data_path}")
    raise SystemExit(1)


total = 0
over_threshold = 0
max_chars = 0
max_title = ""

with open(data_path, encoding="utf-8") as f:
    for line in f:
        article = json.loads(line)
        text = article.get("text", "")
        length = len(text)
        total += 1

        if length > max_chars:
            max_chars = length
            max_title = article.get("title", "?")

        if length > args.threshold:
            over_threshold += 1


print(f"File:              {data_path.name}")
print(f"Threshold:         {args.threshold:,} chars")
print(f"Total articles:    {total:,}")
print(f"Over threshold:    {over_threshold:,}")
print(f"Longest article:   {max_title} ({max_chars:,} chars)")
