import json
from pathlib import Path
from functools import lru_cache
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.core import neologism_reviews

router = APIRouter()

_DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data"
_NEOLOGISMS_FILE = _DATA_DIR / "frequency" / "eswiki_neologisms_occurrences_enriched.json"

@lru_cache(maxsize=1)
def load_neologisms():
    if not _NEOLOGISMS_FILE.exists():
        return []
    with open(_NEOLOGISMS_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
    # Pre-compute word-level min_depth (minimum across all pages, ignoring nulls)
    for item in raw:
        depths = [
            page.get("min_depth")
            for page in item.get("pages", {}).values()
            if page.get("min_depth") is not None
        ]
        item["min_depth"] = min(depths) if depths else None
    return raw

@router.get("/neologisms")
def get_neologisms(
    min_pages: Optional[int] = Query(None, description="Minimum number of pages"),
    max_pages: Optional[int] = Query(None, description="Maximum number of pages"),
    min_freq: Optional[int] = Query(None, description="Minimum total frequency"),
    max_freq: Optional[int] = Query(None, description="Maximum total frequency"),
    min_depth: Optional[int] = Query(None, description="Minimum category depth (word-level)"),
    max_depth: Optional[int] = Query(None, description="Maximum category depth (word-level)"),
    review_status: Optional[str] = Query(None, description="Filter by review status: valid, discarded, unreviewed"),
    limit: int = Query(100, description="Max results to return"),
    offset: int = Query(0, description="Offset for pagination"),
):
    try:
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
        word_depth = item.get("min_depth")
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
