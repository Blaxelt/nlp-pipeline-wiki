import json
import re
from collections import Counter, defaultdict
from pathlib import Path

script_dir  = Path(__file__).resolve().parent
neo_path    = (script_dir / '../../data/frequency/eswiki_neologisms_20260301_20251020_clean.txt').resolve()
json_path   = (script_dir / '../../data/eswiki-20260301-pages-articles-clean.json').resolve()
output_path = (script_dir / '../../data/frequency/eswiki_neologisms_occurrences_clean.json').resolve()

# We use the identical regex from compute_frequencies.py
WORD_RE = re.compile(r"[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+|\d+|[^\w\s]", re.UNICODE)

def main():
    if not neo_path.exists():
        print(f"Error: Neologisms file not found at {neo_path}")
        return
    if not json_path.exists():
        print(f"Error: Wikipedia JSON file not found at {json_path}")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("Loading neologisms set...")
    neologisms = set()
    with neo_path.open("r", encoding="utf-8") as f:
        for line in f:
            word = line.split('\t')[0]
            neologisms.add(word)
    
    print(f"Loaded {len(neologisms):,} neologisms.")
    
    # Data structure: neo_occurrences[word][page_title] = count
    neo_occurrences = defaultdict(Counter)

    print("Streaming Wikipedia articles...")
    processed = 0
    with json_path.open("r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            title = data.get("title", "Unknown Title")
            text = data.get("text", "")
            
            words = WORD_RE.findall(text)
            
            # Count occurrences of neologisms in this article
            for word in words:
                if word in neologisms:
                    neo_occurrences[word][title] += 1
                    
            processed += 1
            if processed % 100_000 == 0:
                print(f"  Processed {processed:,} articles...")

    print(f"Finished processing {processed:,} articles.")
    
    # Prepare output data
    print("Formatting output data...")
    results = []
    
    # Read the original frequencies to preserve sorting
    # Alternatively we can just re-sort by total_freq here
    for word, pages_counter in neo_occurrences.items():
        total_freq = sum(pages_counter.values())
        results.append({
            "word": word,
            "total_freq": total_freq,
            "n_pages": len(pages_counter),
            # Sort pages by frequency descending to make it easier to read
            "pages": dict(pages_counter.most_common())
        })

    # Sort results by total_freq descending
    results.sort(key=lambda x: x["total_freq"], reverse=True)

    print(f"Writing detailed results for {len(results):,} neologisms to {output_path}...")
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print("Done!")

if __name__ == "__main__":
    main()
