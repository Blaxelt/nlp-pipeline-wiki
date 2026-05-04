import json
import logging
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REVIEWS_FILE = DATA_DIR / "neologism_reviews.json"

# In-memory state
_reviews: dict[str, dict] = {}


def load() -> None:
    """Load neologism reviews from disk into memory."""
    global _reviews
    if not REVIEWS_FILE.exists():
        _reviews = {}
        logger.info("No reviews file found at %s — starting empty", REVIEWS_FILE)
        return

    try:
        with open(REVIEWS_FILE, "r", encoding="utf-8") as f:
            _reviews = json.load(f)
        logger.info("Loaded %d neologism reviews from %s", len(_reviews), REVIEWS_FILE)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse reviews file %s: %s", REVIEWS_FILE, e)
        _reviews = {}


def _save() -> None:
    """Persist in-memory reviews to disk."""
    try:
        with open(REVIEWS_FILE, "w", encoding="utf-8") as f:
            json.dump(_reviews, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("Failed to save reviews to %s: %s", REVIEWS_FILE, e)
        raise


def get(word: str) -> dict | None:
    """Return the review for a word, or None if not reviewed."""
    return _reviews.get(word)


def set_review(word: str, status: str, reason: str = "") -> dict:
    """Set or update a review for a word."""
    review = {
        "status": status,
        "reason": reason.strip(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _reviews[word] = review
    _save()
    return review


def all_reviews() -> dict[str, dict]:
    """Return a copy of all reviews."""
    return dict(_reviews)
