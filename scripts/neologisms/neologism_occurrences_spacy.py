import argparse
import json
import multiprocessing as mp
import time
from collections import Counter, defaultdict
from pathlib import Path

import spacy

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"

OUTPUT_DIR = DATA_DIR / "token_frequencies"

parser = argparse.ArgumentParser(
    description="Extract neologism occurrences using spaCy tokenizer"
)

parser.add_argument(
    "--date",
    default="20260301",
    help="Dump date (default: 20260301)",
)

parser.add_argument(
    "--old-date",
    default="20251020",
    help="Old dump date (default: 20251020)",
)

parser.add_argument(
    "--input",
    default=None,
    help="Input JSON file path (overrides --date based default)",
)

parser.add_argument(
    "--input-neologisms",
    default=None,
    help="Path to the neologisms frequency file",
)

parser.add_argument(
    "--output",
    default=None,
    help="Output JSON file path",
)

parser.add_argument(
    "--limit",
    type=int,
    default=None,
    help="Max articles to process (for testing)",
)

parser.add_argument(
    "--processes",
    type=int,
    default=max(1, mp.cpu_count() - 2),
    help="Number of spaCy worker processes",
)

args = parser.parse_args()

MODEL_NAME = "es_core_news_md"
SPACY_BATCH_SIZE = 32
TEXT_BUFFER_SIZE = 256
MAX_CHARS = 600_000
LOG_EVERY = 100_000


def fmt_time(seconds: float) -> str:
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"

    if seconds < 60:
        return f"{seconds:.2f}s"

    m = int(seconds // 60)
    s = seconds % 60

    return f"{m}m {s:.1f}s"


def main():
    t_total = time.perf_counter()

    neo_path = Path(args.input_neologisms) if args.input_neologisms else DATA_DIR / "token_frequencies" / f"eswiki_neologisms_{args.date}_{args.old_date}.txt"

    if args.input:
        data_path = Path(args.input)
    else:
        data_path = (
            DATA_DIR
            / f"eswiki-{args.date}-pages-articles-ns0-no-redirects-clean.json"
        )

    if not data_path.exists():
        print(f"Error: Dump not found at {data_path}")
        raise SystemExit(1)

    if not neo_path.exists():
        print(f"Error: Neologisms file not found at {neo_path}")
        raise SystemExit(1)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_DIR / f"eswiki_neologisms_occurrences_{args.date}_{args.old_date}_spacy.json"

    print("Loading neologisms set...")
    neologisms = set()
    with neo_path.open("r", encoding="utf-8") as f:
        for line in f:
            word = line.split('\t')[0]
            neologisms.add(word)
    
    print(f"Loaded {len(neologisms):,} neologisms.")

    t0 = time.perf_counter()

    nlp = spacy.load(
        MODEL_NAME,
        disable=[
            "tagger",
            "morphologizer",
            "parser",
            "ner",
            "lemmatizer",
            "attribute_ruler",
        ],
    )

    print(
        f"[TIME] Load model:      "
        f"{fmt_time(time.perf_counter() - t0)}  "
        f"({MODEL_NAME})"
    )

    print("\nConfiguration:")
    print(f"  spaCy batch size:    {SPACY_BATCH_SIZE}")
    print(f"  Text buffer size:    {TEXT_BUFFER_SIZE}")
    print(f"  Worker processes:    {args.processes}")
    print(f"  Max chars/article:   {MAX_CHARS:,}")

    t0 = time.perf_counter()

    # Data structure: neo_occurrences[word][page_title] = count
    neo_occurrences = defaultdict(Counter)

    processed = 0
    skipped_long = 0
    total_tokens = 0

    print(f"\nStreaming articles from {data_path.name} ...")

    def process_buffer(items: list[tuple[str, str]]):
        nonlocal total_tokens

        pipe = nlp.pipe(
            items,
            as_tuples=True,
            batch_size=SPACY_BATCH_SIZE,
            n_process=args.processes,
        )

        for doc, title in pipe:
            tokens = [token.text for token in doc if not token.is_space]
            total_tokens += len(tokens)
            
            # Count occurrences of neologisms in this article
            for token in tokens:
                if token in neologisms:
                    neo_occurrences[token][title] += 1

    with open(data_path, encoding="utf-8") as f:
        text_buffer = []

        for line in f:
            article = json.loads(line)

            text = article.get("text", "")
            title = article.get("title", "Unknown Title")

            if not text.strip():
                processed += 1
                continue

            if len(text) > MAX_CHARS:
                text = text[:MAX_CHARS]
                skipped_long += 1

            text_buffer.append((text, title))

            processed += 1

            if len(text_buffer) >= TEXT_BUFFER_SIZE:
                process_buffer(text_buffer)
                text_buffer.clear()

            if args.limit and processed >= args.limit:
                break

            if processed % LOG_EVERY == 0:
                elapsed = time.perf_counter() - t0

                rate = processed / elapsed if elapsed > 0 else 0

                print(
                    f"  Processed {processed:,} articles"
                    f"  |  {fmt_time(elapsed)}"
                    f"  |  {rate:.1f} art/s"
                    f"  |  {total_tokens:,} tokens"
                )

        if text_buffer:
            process_buffer(text_buffer)

    processing_time = time.perf_counter() - t0

    print(f"\n[TIME] Process all:    {fmt_time(processing_time)}")

    print(f"  Articles processed:      {processed:,}")
    print(f"  Articles truncated:      {skipped_long:,}")
    print(f"  Total tokens:            {total_tokens:,}")
    
    # Prepare output data
    print("\nFormatting output data...")
    results = []
    
    for word, pages_counter in neo_occurrences.items():
        total_freq = sum(pages_counter.values())
        results.append({
            "word": word,
            "total_freq": total_freq,
            "n_pages": len(pages_counter),
            "pages": dict(pages_counter.most_common())
        })

    # Sort results by total_freq descending
    results.sort(key=lambda x: x["total_freq"], reverse=True)

    print(f"Writing detailed results for {len(results):,} neologisms to {output_path}...")
    t0 = time.perf_counter()
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print(
        f"[TIME] Write json:     "
        f"{fmt_time(time.perf_counter() - t0)}  "
        f"({output_path.name})"
    )

    print(
        f"\n[TIME] Total:          "
        f"{fmt_time(time.perf_counter() - t_total)}"
    )


if __name__ == "__main__":
    mp.freeze_support()
    main()
