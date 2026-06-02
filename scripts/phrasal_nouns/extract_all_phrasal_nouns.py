import argparse
import json
import multiprocessing as mp
import time
from collections import Counter
from pathlib import Path

import spacy
from spacy.symbols import ADJ, DET, PUNCT, SPACE, SYM

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "phrasal_nouns"

parser = argparse.ArgumentParser(
    description="Extract phrasal nouns from all articles in a dump"
)

parser.add_argument(
    "--date",
    default="20260301",
    help="Dump date (default: 20260301)",
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

    # Fast string checks first
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

    data_path = (
        DATA_DIR
        / f"eswiki-{args.date}-pages-articles-ns0-no-redirects-clean.json"
    )

    if not data_path.exists():
        print(f"Error: Dump not found at {data_path}")
        raise SystemExit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    freq_path = (
        OUTPUT_DIR
        / f"eswiki_{args.date}_phrasal_nouns_freq.txt"
    )

    t0 = time.perf_counter()

    nlp = spacy.load(
        MODEL_NAME,
        disable=[
            "ner",
            "lemmatizer",
            "attribute_ruler",
        ],
    )

    # Keep only what noun_chunks needs
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

    phrase_freq: Counter[str] = Counter()
    no_phrases_titles: list[str] = []

    processed = 0
    skipped_long = 0
    articles_with_phrases = 0
    total_phrases = 0

    print(f"\nStreaming articles from {data_path.name} ...")

    def process_buffer(items: list[tuple[str, str]]):
        nonlocal articles_with_phrases
        nonlocal total_phrases

        texts = [text for _, text in items]
        titles = [title for title, _ in items]

        pipe = nlp.pipe(
            texts,
            batch_size=SPACY_BATCH_SIZE,
            n_process=args.processes,
        )

        for doc, title in zip(pipe, titles):
            article_phrases = set()

            for chunk in doc.noun_chunks:
                if is_valid_chunk(chunk):
                    article_phrases.add(chunk.text.strip())

            if article_phrases:
                articles_with_phrases += 1
                total_phrases += len(article_phrases)

                phrase_freq.update(article_phrases)
            else:
                no_phrases_titles.append(title)

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
                )

        if text_buffer:
            process_buffer(text_buffer)

    processing_time = time.perf_counter() - t0

    print(f"\n[TIME] Process all:    {fmt_time(processing_time)}")

    print(f"  Articles processed:      {processed:,}")
    print(f"  Articles truncated:      {skipped_long:,}")
    print(f"  Articles with phrases:   {articles_with_phrases:,}")
    print(f"  Total phrase instances:  {total_phrases:,}")
    print(f"  Distinct phrases:        {len(phrase_freq):,}")

    print(
        f"  Throughput:              "
        f"{processed / processing_time:.1f} art/s"
    )


    t0 = time.perf_counter()

    sorted_freq = phrase_freq.most_common()

    with open(freq_path, "w", encoding="utf-8") as f:
        write = f.write

        for phrase, freq in sorted_freq:
            write(f"{phrase}\t{freq}\n")

    print(
        f"[TIME] Write freq:     "
        f"{fmt_time(time.perf_counter() - t0)}  "
        f"({freq_path.name})"
    )

    no_phrases_path = (
        OUTPUT_DIR
        / f"eswiki_{args.date}_articles_without_phrases.json"
    )

    t0 = time.perf_counter()

    with open(no_phrases_path, "w", encoding="utf-8") as f:
        json.dump(no_phrases_titles, f, ensure_ascii=False, indent=2)

    print(
        f"[TIME] Write no-phrase:"
        f"{fmt_time(time.perf_counter() - t0)}  "
        f"({no_phrases_path.name}, {len(no_phrases_titles):,} titles)"
    )

    print(
        f"\n[TIME] Total:          "
        f"{fmt_time(time.perf_counter() - t_total)}"
    )


if __name__ == "__main__":
    mp.freeze_support()
    main()