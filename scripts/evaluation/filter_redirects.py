"""
filter_redirects.py
-------------------
Reads the clean Wikipedia NDJSON line by line and writes a new file that
has redirect articles removed.

A redirect is any article whose clean_text starts with:
  #REDIRECCIÓN[[   (Spanish)
  #REDIRECT[[      (English)

Usage
-----
    python scripts/evaluation/filter_redirects.py [--input FILE] [--output FILE]

Defaults:
  --input  data/eswiki-20260301-pages-articles.json
  --output data/eswiki-20260301-pages-articles-no-redirects.json
"""

import argparse
import json
from pathlib import Path


REDIRECT_PREFIXES = ("#REDIRECCIÓN", "#REDIRECT")


def is_redirect(article: dict) -> bool:
    text = article.get("clean_text") or article.get("text", "")
    return text.lstrip().startswith(REDIRECT_PREFIXES)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    base_dir = Path(__file__).resolve().parent.parent.parent

    parser.add_argument(
        "--input",
        default=str(base_dir / "data" / "eswiki-20260301-pages-articles.json"),
        help="Input NDJSON file (default: eswiki-20260301-pages-articles.json)",
    )
    parser.add_argument(
        "--output",
        default=str(base_dir / "data" / "eswiki-20260301-pages-articles-no-redirects.json"),
        help="Output NDJSON file",
    )
    args = parser.parse_args()

    input_path  = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    print(f"Input : {input_path}")
    print(f"Output: {output_path}")
    print("Filtering redirects …")

    total = kept = skipped = 0

    with open(input_path, "rb") as fin, open(output_path, "wb") as fout:
        for raw_line in fin:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            total += 1

            try:
                article = json.loads(raw_line)
            except json.JSONDecodeError:
                skipped += 1
                continue

            if is_redirect(article):
                skipped += 1
            else:
                fout.write(raw_line + b"\n")
                kept += 1

            if total % 100_000 == 0:
                print(f"  {total:,} lines read | {kept:,} kept | {skipped:,} skipped …")

    print(f"\nDone.")
    print(f"  Total lines  : {total:,}")
    print(f"  Kept         : {kept:,}")
    print(f"  Skipped (redirect or bad JSON): {skipped:,}")
    print(f"  Output written to: {output_path}")


if __name__ == "__main__":
    main()
