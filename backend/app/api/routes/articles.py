import json
import re
import urllib.request
from pathlib import Path as FilePath

import wikitextparser as wtp
from fastapi import APIRouter, HTTPException, Path, Query

from app.core import article_store
from app.process_files.extract_entities import extract_entities
from app.process_files.load_bz2 import LoadCancelledError, cancel as cancel_dump, run as load_dump

router = APIRouter()

_DATA_DIR = FilePath(__file__).parent.parent.parent.parent.parent / "data"


@router.get("/articles/available-dumps")
def list_dumps():
    return {"available": article_store.list_available(), "current": article_store.get_current_date()}


@router.get("/articles/remote-dumps")
def remote_dumps():
    try:
        req = urllib.request.Request("https://dumps.wikimedia.org/eswiki/", headers={"User-Agent": "esdbpedia/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Wikimedia dumps page unreachable: {exc}")
    dates = sorted(set(re.findall(r'href="(\d{8})/"', html)), reverse=True)
    return {"dates": dates}


@router.post("/articles/load-existing")
def load_existing(date: str = Query(..., pattern=r"^\d{8}$", description="Dump date in YYYYMMDD format")):
    try:
        article_store.load(date)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"date": date, "status": "loaded"}


@router.post("/articles/load")
def load_articles(date: str = Query(..., pattern=r"^\d{8}$", description="Dump date in YYYYMMDD format, e.g. 20260301")):
    try:
        result = load_dump(date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except LoadCancelledError:
        raise HTTPException(status_code=409, detail="Load cancelled")
    article_store.load(date)  # Reload index into memory after new dump
    return result


@router.post("/articles/load/cancel")
def cancel_load():
    cancel_dump()
    return {"status": "cancellation requested"}


@router.get("/articles/suggest")
def suggest_titles(q: str = Query(..., min_length=1, description="Prefix to search for"), limit: int = Query(10, ge=1, le=50)):
    results = article_store.suggest_titles(q, limit)
    return {"results": results}


@router.get("/articles/by-title/{title}")
def get_article_by_title(title: str = Path(..., title="Article title")):
    article = article_store.get_by_title(title)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return {"text": article["text"], "revision_id": article.get("revision_id"), "title": article.get("title")}


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


def _fetch_wikitext(rev_id: str) -> tuple[str, dict]:
    """Fetch wikitext for a revision from the Wikipedia API.
    Returns (wikitext, page_dict)."""
    api_url = (
        "https://es.wikipedia.org/w/api.php"
        f"?action=query&prop=revisions&revids={rev_id}"
        "&rvprop=content&rvslots=main&format=json"
    )
    req = urllib.request.Request(api_url, headers={"User-Agent": "MSc student (b.tluo@alumnos.upm.es) retrieving wikitext for master thesis (educational use)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        page = next(iter(data["query"]["pages"].values()))
        wikitext = page["revisions"][0]["slots"]["main"]["*"]
        return wikitext, page
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Wikipedia API error: {exc}")


@router.post("/articles/{article_id}/extract-entities")
def extract_article_entities(article_id: str = Path(..., title="Article ID")):
    """Fetch wikitext for the given revision from the Wikipedia API, extract
    wikilink entities, and save them to data/entities/<title>_<id>.json."""
    article = article_store.get(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    wikitext, _ = _fetch_wikitext(article_id)

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


@router.get("/articles/{article_id}/compare-cleaners")
def compare_cleaners(article_id: str = Path(..., title="Article ID")):
    """Fetch wikitext once and run all three cleaning libraries on it."""
    if not article_store.get(article_id):
        raise HTTPException(status_code=404, detail="Article not found")

    wikitext, page = _fetch_wikitext(article_id)

    from app.process_files.cleaners import (
        clean_mwparserfromhell,
        clean_wikiextractor,
        clean_wikitextparser,
    )

    return {
        "wikitextparser": clean_wikitextparser(wikitext),
        "mwparserfromhell": clean_mwparserfromhell(wikitext),
        "wikiextractor": clean_wikiextractor(
            wikitext,
            page_id=str(page.get("pageid", "0")),
            rev_id=article_id,
            title=page.get("title", ""),
        ),
    }