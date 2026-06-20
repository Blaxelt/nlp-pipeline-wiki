import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_PN_DIR = PROJECT_ROOT / "data" / "frequency" / "phrasal_nouns"

def main():
    parser = argparse.ArgumentParser(
        description="Find neologistic phrasal nouns by comparing two extraction dumps."
    )
    parser.add_argument(
        "--old",
        type=str,
        default=str(DEFAULT_PN_DIR / "eswiki_20251020_phrasal_nouns_freq.txt"),
        help="Path to the old phrasal nouns frequency file",
    )
    parser.add_argument(
        "--new",
        type=str,
        default=str(DEFAULT_PN_DIR / "eswiki_20260301_phrasal_nouns_freq.txt"),
        help="Path to the new phrasal nouns frequency file",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(DEFAULT_PN_DIR / "eswiki_neologisms_phrasal_nouns_20260301_20251020.txt"),
        help="Path to save the output neologisms file",
    )
    args = parser.parse_args()

    old_path = Path(args.old)
    new_path = Path(args.new)
    out_path = Path(args.output)

    if not old_path.exists():
        print(f"Error: Old file not found at {old_path}", file=sys.stderr)
        sys.exit(1)
    if not new_path.exists():
        print(f"Error: New file not found at {new_path}", file=sys.stderr)
        sys.exit(1)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Loading old phrasal nouns from {old_path}...")
    old_phrases = set()
    try:
        with old_path.open("r", encoding="utf-8") as f:
            for idx, line in enumerate(f, 1):
                if idx % 5_000_000 == 0:
                    print(f"  Loaded {idx:,} lines...")
                parts = line.rstrip("\n").split("\t")
                if parts:
                    old_phrases.add(parts[0])
    except Exception as e:
        print(f"Error reading old file: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(old_phrases):,} unique old phrasal nouns.")

    print(f"Streaming new phrasal nouns from {new_path}...")
    neologisms = []
    try:
        with new_path.open("r", encoding="utf-8") as f:
            for idx, line in enumerate(f, 1):
                if idx % 5_000_000 == 0:
                    print(f"  Processed {idx:,} lines...")
                parts = line.rstrip("\n").split("\t")
                if len(parts) == 2:
                    phrase, freq_str = parts
                    if phrase not in old_phrases:
                        try:
                            neologisms.append((phrase, int(freq_str)))
                        except ValueError:
                            # Skip lines with malformed frequency
                            continue
    except Exception as e:
        print(f"Error reading new file: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(neologisms):,} neologistic phrasal nouns.")
    print("Sorting neologisms by frequency descending...")
    neologisms.sort(key=lambda x: x[1], reverse=True)

    print(f"Saving sorted neologisms to {out_path}...")
    try:
        with out_path.open("w", encoding="utf-8") as f:
            for phrase, freq in neologisms:
                f.write(f"{phrase}\t{freq}\n")
    except Exception as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        sys.exit(1)

    print("Process completed successfully!")

if __name__ == "__main__":
    main()
