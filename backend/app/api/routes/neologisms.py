import json
from pathlib import Path
from functools import lru_cache
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

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
        filtered_data.append(item)
    
    return {
        "total": len(filtered_data),
        "results": filtered_data[offset:offset + limit]
    }
