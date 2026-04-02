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


def load(date: str) -> None:
    """Load the index for the given dump date into memory."""
    global _ids, _id_to_pos, _offsets, _data_path

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
    logger.info("Article index loaded: %d entries", len(_ids))


def load_latest() -> None:
    """Load the index for the most recent dump found in data/. Used when starting the server."""
    files = sorted(DATA_DIR.glob("eswiki-*-index.json"))
    if not files:
        logger.warning("No index file found in %s — article store is empty", DATA_DIR)
        return
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
