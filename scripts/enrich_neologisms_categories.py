import json
import sys
import time
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FREQ_DIR = DATA_DIR / "frequency"
CAT_DIR = DATA_DIR / "categories"


def main():
    t0 = time.time()

    # Load category data
    print("Loading category_depth.json …")
    with open(CAT_DIR / "category_depth.json", encoding="utf-8") as f:
        cat_depth: dict[str, int] = json.load(f)

    print("Loading article_categories.json …")
    with open(CAT_DIR / "article_categories.json", encoding="utf-8") as f:
        article_cats: dict[str, list[str]] = json.load(f)

    print(f"  Loaded {len(cat_depth):,} category depths, {len(article_cats):,} article→cat mappings")

    # Load neologisms
    print("Loading neologisms …")
    with open(FREQ_DIR / "eswiki_neologisms_occurrences.json", encoding="utf-8") as f:
        neologisms: list[dict] = json.load(f)
    print(f"  {len(neologisms):,} neologism entries")

    # Enrich
    print("Enriching …")
    matched = 0
    unmatched = 0
    for entry in neologisms:
        enriched_pages = {}
        for page_title, freq in entry["pages"].items():
            cats = article_cats.get(page_title, [])
            # Filter to only categories that have a depth (reachable from root)
            depths = [cat_depth[c] for c in cats if c in cat_depth]
            min_d = min(depths) if depths else None

            enriched_pages[page_title] = {
                "freq": freq,
                "categories": cats if cats else None,
                "min_depth": min_d,
            }
            if cats:
                matched += 1
            else:
                unmatched += 1

        entry["pages"] = enriched_pages

    print(f"  Pages matched: {matched:,}, unmatched: {unmatched:,}")

    # Save
    out_path = FREQ_DIR / "eswiki_neologisms_occurrences_enriched.json"
    print(f"Saving to {out_path.name} …")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(neologisms, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - t0
    print(f"Done in {elapsed:.1f}s — {out_path}")


if __name__ == "__main__":
    main()
