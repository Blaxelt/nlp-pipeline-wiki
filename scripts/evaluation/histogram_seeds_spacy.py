import argparse
import json
import random
import spacy
from pathlib import Path
import numpy as np

nlp = spacy.load("es_core_news_sm", disable=["parser", "ner", "tagger", "lemmatizer"])

def load_dictionary(dict_path: Path) -> set:
    print(f"Loading dictionary from {dict_path} …")
    with open(dict_path, "r", encoding="utf-8") as fh:
        words = {line.strip().lower() for line in fh if line.strip()}
    print(f"  → {len(words):,} unique words loaded.")
    return words


def get_random_article(fh, file_size: int) -> dict | None:
    """Seek to a random position in the NDJSON file and return one article."""
    offset = random.randint(0, max(0, file_size - 1))
    fh.seek(offset)
    if offset != 0:
        fh.readline()          # discard partial line
    line = fh.readline()
    if not line:               # hit EOF – wrap around
        fh.seek(0)
        line = fh.readline()
    if not line:
        return None
    try:
        return json.loads(line.decode("utf-8"))
    except json.JSONDecodeError:
        return None


def pct_in_dict(text: str, valid_words: set) -> float | None:
    """Return percentage of tokens found in the dictionary, or None if empty."""
    doc = nlp(text)
    tokens = [token.text.lower() for token in doc if token.is_alpha]
    if not tokens:
        return None
    found = sum(1 for w in tokens if w in valid_words)
    return found / len(tokens) * 100.0


def sample_articles(json_path: Path, valid_words: set, n: int, seed: int) -> list[float]:
    """Return a list of per-article percentages for `n` articles."""
    random.seed(seed)
    file_size = json_path.stat().st_size
    results: list[float] = []

    with open(json_path, "rb") as fh:
        attempts = 0
        while len(results) < n:
            attempts += 1
            if attempts > n * 10:
                print(f"  Warning: too many failed attempts (seed={seed}), stopping early.")
                break
            article = get_random_article(fh, file_size)
            if article is None:
                continue
            text = article.get("clean_text") or article.get("text", "")
            pct = pct_in_dict(text, valid_words)
            if pct is not None:
                results.append(pct)

            if len(results) % 200 == 0 and len(results) > 0:
                print(f"    seed={seed}: {len(results)}/{n} articles sampled …")

    return results

def main():
    parser = argparse.ArgumentParser(description="Histogram seeds variant using spacy.")
    base_dir = Path(__file__).resolve().parent.parent.parent
    parser.add_argument("--n-seeds",    type=int, default=10,   help="Number of random seeds (default: 10)")
    parser.add_argument("--n-articles", type=int, default=1000, help="Articles per seed (default: 1000)")
    parser.add_argument(
        "--input",
        default=str(base_dir / "data" / "eswiki-20260301-pages-articles-clean.json"),
        help="Path to input NDJSON file",
    )
    args = parser.parse_args()

    N_SEEDS    = args.n_seeds
    N_ARTICLES = args.n_articles

    json_path = Path(args.input)
    dict_path = base_dir / "data" / "dictionaries" / "dic_es.txt"

    for p in (json_path, dict_path):
        if not p.exists():
            raise FileNotFoundError(f"Required file not found: {p}")

    valid_words = load_dictionary(dict_path)

    all_data: list[list[float]] = []
    for seed in range(1, N_SEEDS + 1):
        print(f"\n[Seed {seed}/{N_SEEDS}] Sampling {N_ARTICLES} articles …")
        data = sample_articles(json_path, valid_words, N_ARTICLES, seed)
        all_data.append(data)
        print(f"  → {len(data)} valid articles | mean={np.mean(data):.2f}%  std={np.std(data):.2f}%")

    all_flat = [v for run in all_data for v in run]
    print(f"\n=== Final Results ===")
    print(f"Total articles sampled: {len(all_flat)}")
    print(f"Overall Mean Percentage: {np.mean(all_flat):.2f}%")
    print(f"Overall Std Dev: {np.std(all_flat):.2f}%")

if __name__ == "__main__":
    main()
