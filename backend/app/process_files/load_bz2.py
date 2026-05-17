import bz2
import json
import logging
import re
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import wikitextparser as wtp

logger = logging.getLogger(__name__)

DUMP_URL_TEMPLATE = (
    "https://dumps.wikimedia.org/eswiki/{date}/"
    "eswiki-{date}-pages-articles-multistream.xml.bz2"
)

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"


_NAVIGATION_LABELS = {
    "extracto": "Ver",
    "ap": "Artículo principal",
    "artículo principal": "Artículo principal",
    "vt": "Véase también",
    "véase también": "Véase también",
    "cp": "Contenido parcial",
    "ver": "Véase también",
}

_FORMATTING_TEMPLATES = frozenset({"small", "formatnum", "nowrap", "nobold", "nolink"})

_TEMPLATE_PREPROCESS_RE = re.compile(
    r"\{\{\s*(Plantilla:\s*)?"
    r"(Extracto|AP|Artículo[\s_]principal|VT|Véase[\s_]también|CP|Ver|small|formatnum|nowrap|nobold|nolink)"
    r"(?:\s*\|\s*([^{}]*))?\s*\}\}",
    re.IGNORECASE,
)


def _replace_known_template(m: re.Match) -> str:
    name = m.group(2).strip().lower().replace("_", " ")
    args_str = m.group(3)

    positional = []
    if args_str:
        for arg in args_str.split("|"):
            arg = arg.strip()
            if "=" in arg:
                key, _, val = arg.partition("=")
                if key.strip().isdigit():
                    arg = val.strip()
                else:
                    continue
            if arg:
                positional.append(arg)

    if name in _NAVIGATION_LABELS:
        label = _NAVIGATION_LABELS[name]
        if positional:
            return f"[{label}: {', '.join(positional)}]"
        return ""

    if name in _FORMATTING_TEMPLATES:
        return positional[0] if positional else ""

    return m.group(0)


def _preprocess_wikitext(wikitext: str) -> str:
    return _TEMPLATE_PREPROCESS_RE.sub(_replace_known_template, wikitext)


def _get_plain_text(revision, ns):
    text_el = revision.find(f"{ns}text")
    if text_el is None or text_el.text is None:
        return None

    preprocessed = _preprocess_wikitext(text_el.text)
    parsed = wtp.parse(preprocessed)

    for ref in parsed.get_tags("ref"):
        try:
            ref.contents = ""
        except AttributeError:
            pass

    for math in parsed.get_tags("math"):
        try:
            math.contents = ""
        except AttributeError:
            pass

    for table in parsed.tables:
        try:
            table.string = ""
        except Exception:
            pass

    for tpl in parsed.templates:
        try:
            tpl.string = ""
        except Exception:
            pass

    try:
        return parsed.plain_text().strip()
    except AttributeError:
        return re.sub(r"\{\{[^}]*\}\}", "", preprocessed).strip()


def _download_bz2(date: str) -> Path:
    bz2_path = DATA_DIR / f"eswiki-{date}-pages-articles-multistream.xml.bz2"
    if bz2_path.exists():
        logger.info("BZ2 already cached: %s", bz2_path)
        return bz2_path

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    url = DUMP_URL_TEMPLATE.format(date=date)
    logger.info("Downloading %s", url)
    try:
        urllib.request.urlretrieve(url, bz2_path)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise ValueError(f"No dump found for date '{date}'. Check https://dumps.wikimedia.org/eswiki/ for available dates.") from exc
        raise
    logger.info("Download complete: %s", bz2_path)
    return bz2_path


def _process(stream, data_path: Path, index_path: Path) -> tuple[int, int]:
    total, skipped = 0, 0
    context = iter(ET.iterparse(stream, events=("start", "end")))
    _, root = next(context)
    ns = root.tag.split("}")[0] + "}"

    ids: list[str] = []
    offsets: list[int] = []
    title_to_id: dict[str, str] = {}

    with open(data_path, "w", encoding="utf-8") as f:
        for event, elem in context:
            if event == "end" and elem.tag == f"{ns}page":
                title_el = elem.find(f"{ns}title")
                revision = elem.find(f"{ns}revision")
                if revision is None:
                    skipped += 1
                else:
                    rev_id_el = revision.find(f"{ns}id")
                    text = _get_plain_text(revision, ns)
                    if text is None:
                        skipped += 1
                    else:
                        rev_id = rev_id_el.text if rev_id_el is not None else None
                        title = title_el.text if title_el is not None else None
                        record = json.dumps({
                            "revision_id": rev_id,
                            "title": title,
                            "text": text,
                        }, ensure_ascii=False)
                        offset = f.tell()
                        f.write(record + "\n")
                        if rev_id is not None:
                            ids.append(rev_id)
                            offsets.append(offset)
                            if title is not None:
                                title_to_id[title] = rev_id

                        total += 1
                        if total % 500 == 0:
                            logger.info("Written %d pages...", total)
                elem.clear()
                root.clear()

    # Write companion index file
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump({"ids": ids, "offsets": offsets, "title_to_id": title_to_id}, f)
    logger.info("Index written: %d entries", len(ids))

    return total, skipped


def run(date: str) -> dict:
    """Download, decompress and process an eswiki dump for the given date.

    Args:
        date: Dump date in YYYYMMDD format, e.g. '20260301'.

    Returns:
        Dict with keys: data_path, index_path, total_pages, skipped, elapsed_seconds.

    Raises:
        ValueError: If the date format is invalid.
    """
    if not re.fullmatch(r"\d{8}", date):
        raise ValueError(f"Invalid date '{date}': must be 8 digits, e.g. 20260301")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data_path  = DATA_DIR / f"eswiki-{date}-pages-articles-clean.json"
    index_path = DATA_DIR / f"eswiki-{date}-index-clean.json"

    if data_path.exists() and index_path.exists():
        logger.info("Clean output already exists: %s, %s", data_path, index_path)
        with open(index_path, encoding="utf-8") as f:
            idx = json.load(f)
        return {
            "data_path": str(data_path),
            "index_path": str(index_path),
            "total_pages": len(idx.get("ids", [])),
            "skipped": 0,
            "elapsed_seconds": 0.0,
        }

    start = time.time()
    bz2_path = _download_bz2(date)
    with bz2.open(bz2_path, "rb") as stream: # stream is now a file-like object of decompressed XML bytes
        total, skipped = _process(stream, data_path, index_path)
    elapsed = round(time.time() - start, 2)

    logger.info("Done. %d pages written, %d skipped in %ss", total, skipped, elapsed)
    return {
        "data_path": str(data_path),
        "index_path": str(index_path),
        "total_pages": total,
        "skipped": skipped,
        "elapsed_seconds": elapsed,
    }