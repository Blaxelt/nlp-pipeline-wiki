import json
import re
from collections import Counter
from pathlib import Path

script_dir  = Path(__file__).resolve().parent
input_path  = (script_dir / '../../data/eswiki-20260301-pages-articles.json').resolve()
output_path = (script_dir / '../../data/frequency/eswiki_20260301_word_frequencies.txt').resolve()

if not input_path.exists():
    print(f"Error: Input file not found at {input_path}")
    exit(1)

output_path.parent.mkdir(parents=True, exist_ok=True)

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

print(f"\nDone. {i:,} articles, {total_tokens:,} tokens, {len(counter):,} unique words.")

with output_path.open("w", encoding="utf-8") as f:
    for word, freq in counter.most_common():
        f.write(f"{word}\t{freq}\n")

print(f"Frequencies saved to: {output_path}")