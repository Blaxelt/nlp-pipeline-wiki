import json
import urllib.request
from pathlib import Path as FilePath

import wikitextparser as wtp
from fastapi import APIRouter, HTTPException, Path, Query

from app.core import article_store
from app.process_files.extract_entities import extract_entities
from app.process_files.load_bz2 import run as load_dump

router = APIRouter()

_DATA_DIR = FilePath(__file__).parent.parent.parent.parent.parent / "data"


@router.post("/articles/load")
def load_articles(date: str = Query(..., pattern=r"^\d{8}$", description="Dump date in YYYYMMDD format, e.g. 20260301")):
    try:
        result = load_dump(date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    article_store.load(date)  # Reload index into memory after new dump
    return result


@router.get("/articles/{article_id}")
def get_article(article_id: str = Path(..., title="Article ID")):
    article = article_store.get(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return {"text": article["text"]}


@router.get("/articles/{article_id}/next")
def get_next_article(article_id: str = Path(..., title="Article ID")):
    next_id = article_store.get_next_id(article_id)
    if not next_id:
        raise HTTPException(status_code=404, detail="No next article found")
    return {"id": next_id}


@router.get("/articles/{article_id}/prev")
def get_prev_article(article_id: str = Path(..., title="Article ID")):
    prev_id = article_store.get_prev_id(article_id)
    if not prev_id:
        raise HTTPException(status_code=404, detail="No previous article found")
    return {"id": prev_id}


@router.post("/articles/{article_id}/extract-entities")
def extract_article_entities(article_id: str = Path(..., title="Article ID")):
    """Fetch wikitext for the given revision from the Wikipedia API, extract
    wikilink entities, and save them to data/entities/<title>_<id>.json."""
    article = article_store.get(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Fetch original wikitext for this specific revision id
    api_url = (
        "https://es.wikipedia.org/w/api.php"
        f"?action=query&prop=revisions&revids={article_id}"
        "&rvprop=content&rvslots=main&format=json"
    )
    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "MSc student (b.tluo@alumnos.upm.es) retrieving wikitext for master thesis (educational use)"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        pages = data["query"]["pages"]
        page = next(iter(pages.values()))
        wikitext = page["revisions"][0]["slots"]["main"]["*"]
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Wikipedia API error: {exc}")

    # Parse and strip templates
    parsed = wtp.parse(wikitext)
    for tpl in parsed.templates:
        try:
            tpl.string = ""
        except Exception:
            pass

    entities = extract_entities(parsed)

    # Save to data/entities/<title>_<revision_id>.json
    safe_title = (article.get("title") or article_id).replace("/", "_")[:80]
    entities_dir = _DATA_DIR / "entities"
    entities_dir.mkdir(parents=True, exist_ok=True)
    out_path = entities_dir / f"{safe_title}_{article_id}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(entities, f, ensure_ascii=False, indent=2)

    return {"file": str(out_path), "count": len(entities), "entities": entities}