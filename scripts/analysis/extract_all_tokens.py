import argparse
import json
import multiprocessing as mp
import time
from collections import Counter
from pathlib import Path

import spacy

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "token_frequencies"

parser = argparse.ArgumentParser(
    description="Extract token frequencies from all articles in a dump"
)

parser.add_argument(
    "--date",
    default="20260301",
    help="Dump date (default: 20260301)",
)

parser.add_argument(
    "--input",
    default=None,
    help="Input JSON file path (overrides --date based default)",
)

parser.add_argument(
    "--output",
    default=None,
    help="Output frequency file path (overrides --date based default)",
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

    if args.output:
        freq_path = Path(args.output)
        freq_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        freq_path = (
            OUTPUT_DIR
            / f"eswiki_{args.date}_token_frequencies.txt"
        )

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

    token_freq: Counter[str] = Counter()

    processed = 0
    skipped_long = 0
    total_tokens = 0

    print(f"\nStreaming articles from {data_path.name} ...")

    def process_buffer(texts: list[str]):
        nonlocal total_tokens

        pipe = nlp.pipe(
            texts,
            batch_size=SPACY_BATCH_SIZE,
            n_process=args.processes,
        )

        for doc in pipe:
            tokens = [token.text for token in doc if not token.is_space]
            total_tokens += len(tokens)
            token_freq.update(tokens)

    with open(data_path, encoding="utf-8") as f:
        text_buffer = []

        for line in f:
            article = json.loads(line)

            text = article.get("text", "")

            if not text.strip():
                processed += 1
                continue

            if len(text) > MAX_CHARS:
                text = text[:MAX_CHARS]
                skipped_long += 1

            text_buffer.append(text)

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
    print(f"  Distinct tokens:         {len(token_freq):,}")

    print(
        f"  Throughput:              "
        f"{processed / processing_time:.1f} art/s"
    )

    t0 = time.perf_counter()

    sorted_freq = token_freq.most_common()

    with open(freq_path, "w", encoding="utf-8") as f:
        write = f.write

        for token, freq in sorted_freq:
            write(f"{token}\t{freq}\n")

    print(
        f"[TIME] Write freq:     "
        f"{fmt_time(time.perf_counter() - t0)}  "
        f"({freq_path.name})"
    )

    print(
        f"\n[TIME] Total:          "
        f"{fmt_time(time.perf_counter() - t_total)}"
    )


if __name__ == "__main__":
    mp.freeze_support()
    main()
