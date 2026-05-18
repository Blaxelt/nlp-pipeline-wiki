import argparse
import json
import random
import re
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np

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
    tokens = re.findall(r"[a-záéíóúüñ]+", text.lower())
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
    parser = argparse.ArgumentParser(description=__doc__)
    base_dir = Path(__file__).resolve().parent.parent.parent
    parser.add_argument("--n-seeds",    type=int, default=10,   help="Number of random seeds (default: 10)")
    parser.add_argument("--n-articles", type=int, default=1000, help="Articles per seed (default: 1000)")
    parser.add_argument("--bins",       type=int, default=40,   help="Number of histogram bins (default: 40)")
    parser.add_argument(
        "--input",
        default=str(base_dir / "data" / "eswiki-20260301-pages-articles-ns0-no-redirects-clean.json"),
        help="Path to input NDJSON file (default: eswiki-20260301-pages-articles-ns0-no-redirects-clean.json)",
    )
    args = parser.parse_args()

    N_SEEDS    = args.n_seeds
    N_ARTICLES = args.n_articles
    N_BINS     = args.bins

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

    fig, ax = plt.subplots(figsize=(12, 6))

    colors = cm.tab20(np.linspace(0, 1, N_SEEDS))
    bins   = np.linspace(0, 100, N_BINS + 1)

    for i, (data, color) in enumerate(zip(all_data, colors)):
        ax.hist(
            data,
            bins=bins,
            density=True,       # normalise so different sample sizes compare fairly
            alpha=0.35,
            color=color,
            label=f"Seed {i + 1}  (n={len(data)}, μ={np.mean(data):.1f}%)",
            edgecolor="none",
        )

    # Overlay a grand mean KDE-like step line
    all_flat = [v for run in all_data for v in run]
    counts, edges = np.histogram(all_flat, bins=bins, density=True)
    centres = (edges[:-1] + edges[1:]) / 2
    ax.step(centres, counts, where="mid", color="black", linewidth=1.8,
            label=f"All seeds combined (n={len(all_flat):,})")

    ax.set_xlabel("% palabras encontradas en diccionario", fontsize=13)
    ax.set_ylabel("Densidad", fontsize=13)
    ax.set_title(
        f"Distribución del % de palabras en diccionario\n"
        f"{N_SEEDS} semillas × {N_ARTICLES} artículos (es-Wikipedia 2026-03-01)",
        fontsize=14,
    )
    ax.legend(fontsize=8, ncol=2, loc="upper left")
    ax.set_xlim(0, 100)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    out_path = Path(__file__).resolve().parent / f"histogram_seeds{N_SEEDS}_art{N_ARTICLES}_clean_ns0.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\nFigura guardada en: {out_path}")
    plt.show()


if __name__ == "__main__":
    main()
