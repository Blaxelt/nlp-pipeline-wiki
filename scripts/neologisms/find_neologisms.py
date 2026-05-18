from pathlib import Path

script_dir = Path(__file__).resolve().parent
freq_dir   = (script_dir / '../../data/frequency').resolve()

old_path = freq_dir / 'eswiki_20251020_word_frequencies_ns0_clean.txt'
new_path = freq_dir / 'eswiki_20260301_word_frequencies_ns0_clean.txt'
out_path = freq_dir / 'eswiki_neologisms_20260301_20251020_ns0_clean.txt'

def load_tokens(path):
    tokens = {}
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            word, freq = line.rstrip('\n').split('\t')
            tokens[word] = int(freq)
    return tokens

print("Loading old vocab (20251020)...")
old_tokens = load_tokens(old_path)

print("Loading new vocab (20260301)...")
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