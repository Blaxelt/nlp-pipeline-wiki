import argparse
from pathlib import Path

script_dir = Path(__file__).resolve().parent
freq_dir   = (script_dir / '../../data/token_frequencies').resolve() 

def load_tokens(path):
    tokens = {}
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            word, freq = line.rstrip('\n').split('\t')
            tokens[word] = int(freq)
    return tokens

def main():
    parser = argparse.ArgumentParser(
        description="Find neologisms by comparing two token frequency dumps."
    )
    parser.add_argument(
        "--date",
        default="20260301",
        help="New dump date (default: 20260301)",
    )
    parser.add_argument(
        "--old-date",
        default="20251020",
        help="Old dump date (default: 20251020)",
    )
    args = parser.parse_args()

    old_path = freq_dir / f'eswiki_{args.old_date}_token_frequencies.txt'
    new_path = freq_dir / f'eswiki_{args.date}_token_frequencies.txt'
    out_path = freq_dir / f'eswiki_neologisms_{args.date}_{args.old_date}.txt'

    print(f"Loading old vocab ({args.old_date})...")
    old_tokens = load_tokens(old_path)

    print(f"Loading new vocab ({args.date})...")
    new_tokens = load_tokens(new_path)

    # Tokens in new that are completely absent from old
    neologisms = {
        word: freq
        for word, freq in new_tokens.items()
        if word not in old_tokens
    }

    print(f"\nOld vocab size : {len(old_tokens):,}")
    print(f"New vocab size : {len(new_tokens):,}")
    print(f"Neologisms     : {len(neologisms):,}")

    # Sort by frequency descending so the most-used new words come first
    sorted_neo = sorted(neologisms.items(), key=lambda x: x[1], reverse=True)

    with out_path.open('w', encoding='utf-8') as f:
        for word, freq in sorted_neo:
            f.write(f"{word}\t{freq}\n")

    print(f"Saved to: {out_path}")

if __name__ == '__main__':
    main()