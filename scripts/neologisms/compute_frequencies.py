import argparse
import json
import re
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "token_frequencies"

parser = argparse.ArgumentParser(
    description="Compute word frequencies using regex tokenization"
)

parser.add_argument(
    "--date",
    default="20260301",
    help="Dump date (default: 20260301)",
)

parser.add_argument(
    "--limit",
    type=int,
    default=None,
    help="Max articles to process (for testing)",
)

args = parser.parse_args()

input_path = (
    DATA_DIR
    / f"eswiki-{args.date}-pages-articles-ns0-no-redirects-clean.json"
)

if not input_path.exists():
    print(f"Error: Input file not found at {input_path}")
    exit(1)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

limit_suffix = f"_{args.limit}" if args.limit else ""
output_path = (
    OUTPUT_DIR
    / f"eswiki_{args.date}_regex_frequencies{limit_suffix}.txt"
)

# Matches words (with Spanish chars), numbers, or individual punctuation/symbols
WORD_RE = re.compile(r"[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+|\d+|[^\w\s]", re.UNICODE)

counter = Counter()
total_tokens = 0

with input_path.open("r", encoding="utf-8") as f:
    for i, line in enumerate(f, start=1):
        data = json.loads(line)
        text = data.get("text", "")

        words = WORD_RE.findall(text)
        counter.update(words)
        total_tokens += len(words)

        if i % 1000 == 0:
            print(f"  Processed {i:,} articles | {total_tokens:,} tokens | {len(counter):,} unique")

        if args.limit and i >= args.limit:
            break

print(f"\nDone. {i:,} articles, {total_tokens:,} tokens, {len(counter):,} unique words.")

with output_path.open("w", encoding="utf-8") as f:
    for word, freq in counter.most_common():
        f.write(f"{word}\t{freq}\n")

print(f"Frequencies saved to: {output_path}")