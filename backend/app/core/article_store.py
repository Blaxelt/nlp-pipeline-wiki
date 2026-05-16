import bisect
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# In-memory state
_ids: list[str] = []           # ordered list of revision_ids
_id_to_pos: dict[str, int] = {}  # revision_id → position in _ids
_offsets: list[int] = []       # byte offset per position
_data_path: Path | None = None  # path to the NDJSON data file
_title_to_id: dict[str, str] = {}  # original title → revision_id
_lower_to_id: dict[str, str] = {}  # lowercase title → revision_id
_sorted_titles: list[tuple[str, str]] = []  # (lowercase_title, original_title) sorted by lowercase
_current_date: str | None = None


def _normalize_title(title: str) -> str:
    """Replace spaces with underscores for consistent lookup."""
    return title.replace(" ", "_")


def list_available() -> list[str]:
    """Return list of available dump dates, newest first."""
    dates: set[str] = set()
    for path in DATA_DIR.glob("eswiki-*-index*.json"):
        parts = path.name.split("-")
        if len(parts) < 2:
            continue
        dates.add(parts[1])
    return sorted(dates, reverse=True)


def get_current_date() -> str | None:
    """Return the date of the currently loaded dump, or None."""
    return _current_date


def load(date: str) -> None:
    """Load the index for the given dump date into memory."""
    global _ids, _id_to_pos, _offsets, _data_path
    global _title_to_id, _lower_to_id, _sorted_titles, _current_date

    # Prefer -clean files (improved text extraction), fall back to original
    index_path = DATA_DIR / f"eswiki-{date}-index-clean.json"
    data_path  = DATA_DIR / f"eswiki-{date}-pages-articles-clean.json"
    if not index_path.exists() or not data_path.exists():
        index_path = DATA_DIR / f"eswiki-{date}-index.json"
        data_path  = DATA_DIR / f"eswiki-{date}-pages-articles.json"

    if not index_path.exists():
        raise FileNotFoundError(f"Index file not found: {index_path}")
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")

    logger.info("Loading article index from %s", index_path)
    with open(index_path, encoding="utf-8") as f:
        idx = json.load(f)

    _ids = idx["ids"]
    _offsets = idx["offsets"]
    _id_to_pos = {rid: pos for pos, rid in enumerate(_ids)}
    _data_path = data_path

    _title_to_id = idx.get("title_to_id", {})
    _lower_to_id = {}
    _sorted_titles = []
    for orig_title, rev_id in _title_to_id.items():
        normalized = _normalize_title(orig_title)
        lower = normalized.lower()
        _lower_to_id[lower] = rev_id
        _sorted_titles.append((lower, normalized))
    _sorted_titles.sort(key=lambda x: x[0])

    _current_date = date
    logger.info("Article index loaded: %d entries, %d titles", len(_ids), len(_title_to_id))


def load_latest() -> None:
    """Load the index for the most recent dump found in data/. Used when starting the server."""
    # Prefer -clean index files, fall back to original
    files = sorted(DATA_DIR.glob("eswiki-*-index-clean.json"))
    if not files:
        files = sorted(DATA_DIR.glob("eswiki-*-index.json"))
    if not files:
        logger.warning("No index file found in %s — article store is empty", DATA_DIR)
        return
    # Extract date: eswiki-20260301-index-clean.json -> 20260301
    date = files[-1].name.split("-")[1]
    load(date)


def get(revision_id: str) -> dict | None:
    """Return the article record for the given revision_id, or None if not found."""
    if _data_path is None:
        return None
    pos = _id_to_pos.get(revision_id)
    if pos is None:
        return None
    with open(_data_path, encoding="utf-8") as f:
        f.seek(_offsets[pos])
        return json.loads(f.readline())


def get_by_title(title: str) -> dict | None:
    """Return the article record for the given title (case-insensitive), or None."""
    normalized = _normalize_title(title).lower()
    rev_id = _lower_to_id.get(normalized)
    if rev_id is None:
        return None
    return get(rev_id)


def suggest_titles(prefix: str, limit: int = 10) -> list[dict]:
    """Return up to *limit* titles whose lowercase form starts with *prefix* (case-insensitive).

    Each result is a dict with keys: title (normalized with underscores), revision_id.
    """
    if not _sorted_titles or not prefix:
        return []
    prefix_lower = _normalize_title(prefix).lower()
    idx = bisect.bisect_left(_sorted_titles, prefix_lower, key=lambda x: x[0])
    results: list[dict] = []
    seen: set[str] = set()
    for i in range(idx, len(_sorted_titles)):
        if len(results) >= limit:
            break
        lower, normalized = _sorted_titles[i]
        if not lower.startswith(prefix_lower):
            break
        if normalized in seen:
            continue
        seen.add(normalized)
        rev_id = _lower_to_id.get(lower)
        if rev_id is not None:
            results.append({"title": normalized, "revision_id": rev_id})
    return results


def get_next_id(revision_id: str) -> str | None:
    """Return the revision_id of the next article, or None if at the end."""
    pos = _id_to_pos.get(revision_id)
    if pos is None or pos + 1 >= len(_ids):
        return None
    return _ids[pos + 1]


def get_prev_id(revision_id: str) -> str | None:
    """Return the revision_id of the previous article, or None if at the start."""
    pos = _id_to_pos.get(revision_id)
    if pos is None or pos == 0:
        return None
    return _ids[pos - 1]
