import logging
from pathlib import Path

logger = logging.getLogger(__name__)

wikipedia_index: dict[str, set[str]] = {"es": set(), "en": set()}

ROOT_DIR = Path(__file__).parents[3]

INDEX_DIR = ROOT_DIR / "index"


def _find_latest_index(lang: str) -> Path | None:
    prefix = f"{lang}wiki-"
    files = sorted(INDEX_DIR.glob(f"{prefix}*-pages-articles-multistream-index.txt"))
    return files[-1] if files else None


def load_index(lang: str):
    path = _find_latest_index(lang)
    if path is None:
        logger.warning("[%s] No index file found in %s — URL validation disabled for this language", lang, INDEX_DIR)
        wikipedia_index[lang] = set()
        return
    logger.info("[%s] Cargando índice desde %s …", lang, path)
    titles = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.count(":") == 2:
                title = line.strip().split(":")[2].replace(" ", "_")
                titles.add(title)
    wikipedia_index[lang] = titles
    logger.info("[%s] %s titles and redirects loaded", lang, f"{len(titles):,}")


def load_all():
    for lang in ["es", "en"]:
        load_index(lang)