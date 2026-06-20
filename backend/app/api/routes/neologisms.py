import json
from pathlib import Path
from functools import lru_cache
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.core import neologism_reviews

router = APIRouter()

_DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data"
_NEOLOGISMS_FILE = _DATA_DIR / "token_frequencies" / "eswiki_neologisms_occurrences_clean_spacy_enriched.json"
_PHRASAL_NEOLOGISMS_FILE = _DATA_DIR / "frequency" / "phrasal_nouns" / "eswiki_neologisms_phrasal_nouns_occurrences_enriched.json"


def _precompute_depths(raw: list[dict]) -> list[dict]:
    """Pre-compute word-level mean_depth and num_categories."""
    for item in raw:
        depths = []
        distinct_cats: set[str] = set()
        for page in item.get("pages", {}).values():
            d = page.get("mean_depth") if page.get("mean_depth") is not None else page.get("min_depth")
            if d is not None:
                depths.append(d)
            cats = page.get("categories")
            if cats:
                distinct_cats.update(cats)
        item["mean_depth"] = round(sum(depths) / len(depths), 2) if depths else None
        item["num_categories"] = len(distinct_cats)
    return raw


@lru_cache(maxsize=1)
def load_neologisms():
    if not _NEOLOGISMS_FILE.exists():
        return []
    with open(_NEOLOGISMS_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return _precompute_depths(raw)


@lru_cache(maxsize=1)
def load_phrasal_neologisms():
    if not _PHRASAL_NEOLOGISMS_FILE.exists():
        return []
    with open(_PHRASAL_NEOLOGISMS_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return _precompute_depths(raw)


@router.get("/neologisms")
def get_neologisms(
    type: str = Query("words", description="Type of neologisms: 'words' or 'phrasal'"),
    min_pages: Optional[int] = Query(None, description="Minimum number of pages"),
    max_pages: Optional[int] = Query(None, description="Maximum number of pages"),
    min_freq: Optional[int] = Query(None, description="Minimum total frequency"),
    max_freq: Optional[int] = Query(None, description="Maximum total frequency"),
    min_depth: Optional[int] = Query(None, description="Minimum mean category depth (word-level)"),
    max_depth: Optional[int] = Query(None, description="Maximum mean category depth (word-level)"),
    review_status: Optional[str] = Query(None, description="Filter by review status: valid, discarded, unreviewed"),
    limit: int = Query(100, description="Max results to return"),
    offset: int = Query(0, description="Offset for pagination"),
):
    try:
        if type == "phrasal":
            data = load_phrasal_neologisms()
        else:
            data = load_neologisms()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    filtered_data = []
    for item in data:
        if min_pages is not None and item.get("n_pages", 0) < min_pages:
            continue
        if max_pages is not None and item.get("n_pages", 0) > max_pages:
            continue
        if min_freq is not None and item.get("total_freq", 0) < min_freq:
            continue
        if max_freq is not None and item.get("total_freq", 0) > max_freq:
            continue
        word_depth = item.get("mean_depth")
        if min_depth is not None:
            if word_depth is None or word_depth < min_depth:
                continue
        if max_depth is not None:
            if word_depth is None or word_depth > max_depth:
                continue
        
        # Attach review info
        review = neologism_reviews.get(item["word"])
        item["review"] = review
        
        # Filter by review status
        if review_status:
            if review_status == "unreviewed":
                if review is not None:
                    continue
            elif review_status in ("valid", "discarded"):
                if review is None or review.get("status") != review_status:
                    continue
        
        filtered_data.append(item)
    
    return {
        "total": len(filtered_data),
        "results": filtered_data[offset:offset + limit]
    }


@router.post("/neologisms/review")
def post_review(payload: dict):
    """Save or update a review for a neologism.
    
    Body: {"word": "...", "status": "valid|discarded", "reason": "..."}
    """
    word = payload.get("word")
    status = payload.get("status")
    reason = payload.get("reason", "")
    
    if not word:
        raise HTTPException(status_code=400, detail="Missing 'word' field")
    if status not in ("valid", "discarded"):
        raise HTTPException(status_code=400, detail="Status must be 'valid' or 'discarded'")
    
    review = neologism_reviews.set_review(word, status, reason)
    return {"word": word, "review": review}
