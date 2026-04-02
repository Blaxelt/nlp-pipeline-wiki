from pathlib import Path

wikipedia_index: dict[str, set[str]] = {"es": set(), "en": set()}

ROOT_DIR = Path(__file__).parents[3]

INDEX_FILES = {
    "es": ROOT_DIR / "index" / "eswiki-20260301-pages-articles-multistream-index.txt",
    "en": ROOT_DIR / "index" / "enwiki-20260301-pages-articles-multistream-index.txt",
}

def load_index(lang: str):
    path = Path(INDEX_FILES[lang])
    print(f"[{lang}] Cargando índice desde {path}...")
    titles = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.count(":") == 2: # Skip lines that are extra pages.
                title = line.strip().split(":")[2].replace(" ", "_")
                titles.add(title)
    wikipedia_index[lang] = titles
    print(f"[{lang}] {len(titles):,} titles and redirects loaded")

def load_all():
    for lang in ["es", "en"]:
        load_index(lang)