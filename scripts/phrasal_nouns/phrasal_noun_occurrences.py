"""
Find per-article occurrences of neologistic phrasal nouns.

Uses the same spaCy pipeline and is_valid_chunk() logic as
extract_all_phrasal_nouns.py to guarantee identical noun-chunk
extraction.  Only records data for phrases that are in the
neologism set.
"""

import argparse
import json
import multiprocessing as mp
import time
from collections import Counter, defaultdict
from pathlib import Path

import spacy
from spacy.symbols import ADJ, DET, PUNCT, SPACE, SYM

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PN_FREQ_DIR = DATA_DIR / "frequency" / "phrasal_nouns"

parser = argparse.ArgumentParser(
    description="Find per-article occurrences of neologistic phrasal nouns"
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
    "--neologisms",
    type=str,
    default=None,
    help="Path to the neologistic phrasal nouns file (tab-separated)",
)

parser.add_argument(
    "--input",
    default=None,
    help="Input JSON file path (overrides --date based default)",
)

parser.add_argument(
    "--input-neologisms",
    default=None,
    help="Path to the neologisms frequency file (alias for --neologisms)",
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



INVALID_POS = {SPACE, PUNCT}
IGNORED_POS = {DET, PUNCT, SPACE, SYM}
SHORT_IGNORE_POS = {DET, PUNCT, SPACE, SYM, ADJ}

INVALID_START_CHARS = {
    ",", ".", ":", ";", "-", "(", ")", "[", "]",
    '"', "'", "*", "=", "|", "#"
}


def is_valid_chunk(chunk) -> bool:
    raw = chunk.text

    if not raw:
        return False

    text = raw.strip()

    if not text:
        return False

    if "\n" in raw:
        return False

    if "===" in raw:
        return False

    if "==" in text:
        return False

    if text.endswith(("]", ")")):
        return False

    if text[0] in INVALID_START_CHARS:
        return False

    real_token_count = 0
    has_meaningful = False
    has_long_non_adj = False
    first_real_pos = None

    for token in chunk:
        pos = token.pos

        if pos not in INVALID_POS:
            real_token_count += 1

            if first_real_pos is None:
                first_real_pos = pos

        if pos not in IGNORED_POS:
            has_meaningful = True

        if len(token.text) > 2 and pos not in SHORT_IGNORE_POS:
            has_long_non_adj = True

    if real_token_count < 2:
        return False

    if real_token_count == 2 and first_real_pos == DET:
        return False

    if not has_meaningful:
        return False

    if not has_long_non_adj:
        return False

    return True



def main():
    t_total = time.perf_counter()

    neo_src = args.input_neologisms or args.neologisms
    neo_path = Path(neo_src) if neo_src else PN_FREQ_DIR / f'eswiki_neologisms_phrasal_nouns_{args.date}_{args.old_date}.txt'
    if not neo_path.exists():
        print(f"Error: Neologisms file not found at {neo_path}")
        raise SystemExit(1)

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
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        PN_FREQ_DIR.mkdir(parents=True, exist_ok=True)
        out_path = PN_FREQ_DIR / f'eswiki_neologisms_phrasal_nouns_occurrences_{args.date}_{args.old_date}.json'

    t0 = time.perf_counter()

    neologism_set: set[str] = set()
    with neo_path.open("r", encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if parts:
                neologism_set.add(parts[0])

    print(f"[TIME] Load neologisms: {fmt_time(time.perf_counter() - t0)}")
    print(f"  {len(neologism_set):,} neologistic phrasal nouns to search for")

    t0 = time.perf_counter()

    nlp = spacy.load(
        MODEL_NAME,
        disable=[
            "ner",
            "lemmatizer",
            "attribute_ruler",
        ],
    )

    nlp.select_pipes(enable=[
        "tok2vec",
        "tagger",
        "morphologizer",
        "parser",
    ])

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

    # neo_occurrences[phrase][page_title] = count
    neo_occurrences: dict[str, Counter] = defaultdict(Counter)

    processed = 0
    skipped_long = 0
    matched_articles = 0
    total_matches = 0

    print(f"\nStreaming articles from {data_path.name} ...")

    def process_buffer(items: list[tuple[str, str]]):
        nonlocal matched_articles
        nonlocal total_matches

        texts = [text for _, text in items]
        titles = [title for title, _ in items]

        pipe = nlp.pipe(
            texts,
            batch_size=SPACY_BATCH_SIZE,
            n_process=args.processes,
        )

        for doc, title in zip(pipe, titles):
            article_matched = False

            for chunk in doc.noun_chunks:
                if not is_valid_chunk(chunk):
                    continue

                phrase = chunk.text.strip()

                if phrase in neologism_set:
                    neo_occurrences[phrase][title] += 1
                    total_matches += 1
                    article_matched = True

            if article_matched:
                matched_articles += 1

    with open(data_path, encoding="utf-8") as f:
        text_buffer: list[tuple[str, str]] = []

        for line in f:
            article = json.loads(line)

            text = article.get("text", "")
            title = article.get("title", "")

            if not text.strip():
                processed += 1
                continue

            if len(text) > MAX_CHARS:
                text = text[:MAX_CHARS]
                skipped_long += 1

            text_buffer.append((title, text))

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
                    f"  |  {total_matches:,} matches"
                    f"  |  {len(neo_occurrences):,} distinct"
                )

        if text_buffer:
            process_buffer(text_buffer)

    processing_time = time.perf_counter() - t0

    print(f"\n[TIME] Process all:     {fmt_time(processing_time)}")
    print(f"  Articles processed:       {processed:,}")
    print(f"  Articles truncated:       {skipped_long:,}")
    print(f"  Articles with matches:    {matched_articles:,}")
    print(f"  Total phrase matches:     {total_matches:,}")
    print(f"  Distinct phrases found:   {len(neo_occurrences):,}")

    if processing_time > 0:
        print(
            f"  Throughput:               "
            f"{processed / processing_time:.1f} art/s"
        )

    t0 = time.perf_counter()

    results = []
    for phrase, pages_counter in neo_occurrences.items():
        total_freq = sum(pages_counter.values())
        results.append({
            "word": phrase,
            "total_freq": total_freq,
            "n_pages": len(pages_counter),
            "pages": dict(pages_counter.most_common()),
        })

    results.sort(key=lambda x: x["total_freq"], reverse=True)

    print(f"\nWriting {len(results):,} phrasal neologism occurrences to {out_path.name} ...")
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"[TIME] Write output:    {fmt_time(time.perf_counter() - t0)}")
    print(
        f"\n[TIME] Total:           "
        f"{fmt_time(time.perf_counter() - t_total)}"
    )
    print("Done!")


if __name__ == "__main__":
    mp.freeze_support()
    main()
