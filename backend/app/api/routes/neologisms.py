import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.core import neologism_reviews

router = APIRouter()

_DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data"

# Module-level state for loaded data
_words_data: list[dict] | None = None
_words_file: str | None = None
_phrasal_data: list[dict] | None = None
_phrasal_file: str | None = None


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


def _load_file(rel_path: str) -> list[dict]:
    """Load and precompute a neologism JSON file given a path relative to data/."""
    full_path = (_DATA_DIR / rel_path).resolve()
    # Security: ensure path stays within data dir
    if not str(full_path).startswith(str(_DATA_DIR.resolve())):
        raise ValueError("Invalid path")
    if not full_path.exists():
        return []
    with open(full_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return _precompute_depths(raw)


def _get_words_data() -> list[dict]:
    if _words_data is None:
        return []
    return _words_data


def _get_phrasal_data() -> list[dict]:
    if _phrasal_data is None:
        return []
    return _phrasal_data


def _discover_files() -> dict[str, list[dict]]:
    """Discover neologism JSON files in data/ directory."""
    words_files = []
    phrasal_files = []

    for json_file in sorted(_DATA_DIR.rglob("*.json")):
        name = json_file.name.lower()
        # Only include enriched neologism/phrasal files
        if "enriched" not in name:
            continue
        if "neologism" not in name and "phrasal" not in name:
            continue

        rel_path = str(json_file.relative_to(_DATA_DIR))
        entry = {"path": rel_path, "name": json_file.name}

        if "phrasal" in name:
            phrasal_files.append(entry)
        else:
            words_files.append(entry)

    return {"words": words_files, "phrasal": phrasal_files}


@router.get("/neologisms/available-files")
def list_available_files():
    files = _discover_files()
    return {
        **files,
        "current": {
            "words": _words_file,
            "phrasal": _phrasal_file,
        }
    }


@router.post("/neologisms/load")
def load_neologism_file(payload: dict):
    """Load a specific neologism file.

    Body: {"type": "words"|"phrasal", "path": "relative/path.json"}
    """
    global _words_data, _words_file, _phrasal_data, _phrasal_file

    neo_type = payload.get("type")
    rel_path = payload.get("path")

    if neo_type not in ("words", "phrasal"):
        raise HTTPException(status_code=400, detail="type must be 'words' or 'phrasal'")
    if not rel_path:
        raise HTTPException(status_code=400, detail="Missing 'path' field")

    try:
        data = _load_file(rel_path)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if neo_type == "words":
        _words_data = data
        _words_file = rel_path
    else:
        _phrasal_data = data
        _phrasal_file = rel_path

    return {"status": "loaded", "type": neo_type, "path": rel_path, "count": len(data)}


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
            data = _get_phrasal_data()
        else:
            data = _get_words_data()
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
        
        # Attach review info via a shallow copy to avoid mutating cached data
        review = neologism_reviews.get(item["word"])
        
        # Filter by review status
        if review_status:
            if review_status == "unreviewed":
                if review is not None:
                    continue
            elif review_status in ("valid", "discarded"):
                if review is None or review.get("status") != review_status:
                    continue
        
        filtered_data.append({**item, "review": review})
    
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
