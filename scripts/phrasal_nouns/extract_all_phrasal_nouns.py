import argparse
import json
import time
from collections import Counter
from pathlib import Path

import spacy

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "phrasal_nouns"

parser = argparse.ArgumentParser(description="Extract phrasal nouns from all articles in a dump")
parser.add_argument("--date", default="20260301", help="Dump date (default: 20260301)")
parser.add_argument("--limit", type=int, default=None, help="Max articles to process (for testing)")
args = parser.parse_args()


def fmt_time(seconds: float) -> str:
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.2f}s"
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m}m {s:.1f}s"


def is_valid_chunk(chunk) -> bool:
    raw = chunk.text
    text = raw.strip()
    tokens = list(chunk)

    if not text:
        return False

    if "\n" in raw or "===" in raw:
        return False

    if text.endswith("]") or text.endswith(")"):
        return False

    if text[0] in {",", ".", ":", ";", "-", "(", ")", "[", "]", '"', "'", "*", "=", "|", "#"}:
        return False

    if "==" in text:
        return False

    real_tokens = [t for t in tokens if t.pos_ not in {"SPACE", "PUNCT"}]

    if len(real_tokens) < 2:
        return False

    if len(real_tokens) == 2 and real_tokens[0].pos_ == "DET":
        return False

    if not any(t.pos_ not in {"DET", "PUNCT", "SPACE", "SYM"} for t in tokens):
        return False

    if not any(len(t.text) > 2 and t.pos_ not in {"DET", "PUNCT", "SPACE", "SYM", "ADJ"} for t in tokens):
        return False

    return True


def main():
    t_total = time.perf_counter()

    data_path = DATA_DIR / f"eswiki-{args.date}-pages-articles-ns0-no-redirects-clean.json"
    if not data_path.exists():
        print(f"Error: Dump not found at {data_path}")
        exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    freq_path = OUTPUT_DIR / f"eswiki_{args.date}_phrasal_nouns_freq.txt"

    # --- Load spaCy model ---
    t0 = time.perf_counter()
    MODEL_NAME = "es_core_news_md"
    nlp = spacy.load(MODEL_NAME)
    nlp.select_pipes(disable=["ner"])
    print(f"[TIME] Load model:      {fmt_time(time.perf_counter() - t0)}  ({MODEL_NAME})")

    # --- Stream articles and extract phrasal nouns ---
    t0 = time.perf_counter()
    phrase_freq: Counter = Counter()

    processed = 0
    skipped_long = 0
    articles_with_phrases = 0
    total_phrases = 0
    BATCH_SIZE = 50
    MAX_CHARS = 500_000  # Truncate very long articles to avoid memory issues

    print(f"Streaming articles from {data_path.name} ...")
    print(f"  Batch size: {BATCH_SIZE}, Max chars per article: {MAX_CHARS:,}")

    def process_batch(texts):
        nonlocal articles_with_phrases, total_phrases
        for doc in nlp.pipe(texts, batch_size=BATCH_SIZE):
            article_phrases: set[str] = set()
            for chunk in doc.noun_chunks:
                if is_valid_chunk(chunk):
                    article_phrases.add(chunk.text.strip())
            if article_phrases:
                articles_with_phrases += 1
                total_phrases += len(article_phrases)
                for phrase in article_phrases:
                    phrase_freq[phrase] += 1

    with open(data_path, encoding="utf-8") as f:
        batch_texts: list[str] = []

        for line in f:
            article = json.loads(line)
            text = article.get("text", "")

            if not text.strip():
                processed += 1
                continue

            if len(text) > MAX_CHARS:
                text = text[:MAX_CHARS]
                skipped_long += 1

            batch_texts.append(text)
            processed += 1

            if len(batch_texts) >= BATCH_SIZE:
                process_batch(batch_texts)
                batch_texts = []

            if args.limit and processed >= args.limit:
                break

            if processed % 100_000 == 0:
                elapsed = time.perf_counter() - t0
                rate = processed / elapsed if elapsed > 0 else 0
                print(f"  Processed {processed:,} articles  |  {fmt_time(elapsed)}  |  {rate:.1f} art/s")

        # Process remaining articles in the last batch
        if batch_texts:
            process_batch(batch_texts)

    print(f"[TIME] Process all:    {fmt_time(time.perf_counter() - t0)}")
    print(f"  Articles processed:      {processed:,}")
    print(f"  Articles truncated:      {skipped_long:,}")
    print(f"  Articles with phrases:   {articles_with_phrases:,}")
    print(f"  Total phrase instances:  {total_phrases:,}")
    print(f"  Distinct phrases:        {len(phrase_freq):,}")

    # --- Write frequency file ---
    t0 = time.perf_counter()
    sorted_freq = phrase_freq.most_common()
    with open(freq_path, "w", encoding="utf-8") as f:
        for phrase, freq in sorted_freq:
            f.write(f"{phrase}\t{freq}\n")
    print(f"[TIME] Write freq:     {fmt_time(time.perf_counter() - t0)}  ({freq_path.name})")

    print(f"\n[TIME] Total:          {fmt_time(time.perf_counter() - t_total)}")


if __name__ == "__main__":
    main()
