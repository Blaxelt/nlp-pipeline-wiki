import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_FILE = ROOT_DIR / "data" / "redirects_map.json"

REDIRECT_PREFIXES = ("#REDIRECCIÓN", "#REDIRECT")

def is_redirect(article: dict) -> bool:
    text = article.get("clean_text") or article.get("text", "")
    return text.lstrip().upper().startswith(REDIRECT_PREFIXES)

def get_redirect_target(text: str) -> str:
    match = re.search(r'#(?:REDIRECCIÓN|REDIRECT)\s*:?\s*(?:\[\[)?([^\]\n|]+)', text, re.IGNORECASE)
    if match:
        target = match.group(1).strip()
        if target:
            target = target[0].upper() + target[1:]
        return target
    return ""

def main():
    parser = argparse.ArgumentParser(
        description="Extract redirect mappings from a Wikipedia dump."
    )
    parser.add_argument(
        "--date",
        default="20260301",
        help="Dump date (default: 20260301)",
    )
    args = parser.parse_args()

    INPUT_FILE = ROOT_DIR / "data" / f"eswiki-{args.date}-pages-articles-ns0-clean.json"

    redirects_map = defaultdict(list)
    
    print(f"Reading from: {INPUT_FILE}")
    if not INPUT_FILE.exists():
        print(f"Error: Could not find {INPUT_FILE}")
        return

    processed = 0
    redirects_count = 0

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            processed += 1
            if processed % 500000 == 0:
                print(f"Processed {processed} articles...")

            try:
                article = json.loads(line)
                if is_redirect(article):
                    source = article.get("title", "")
                    text = article.get("clean_text") or article.get("text", "")
                    target = get_redirect_target(text)
                    
                    if target and source:
                        redirects_map[target].append(source)
                        redirects_count += 1
            except json.JSONDecodeError:
                continue

    print(f"\nFinished reading. Found {redirects_count} total redirects targeting {len(redirects_map)} unique articles.")
    
    print(f"Writing results to: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out_f:
        json.dump(dict(redirects_map), out_f, ensure_ascii=False, indent=2)
        
    print("Done!")

if __name__ == "__main__":
    main()
