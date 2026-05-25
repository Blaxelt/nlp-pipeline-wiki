import argparse
import json
import time
from pathlib import Path

import spacy

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "phrasal_nouns"

parser = argparse.ArgumentParser(description="Extract phrasal nouns for a single article by revision ID")
parser.add_argument("revision_id", help="Revision ID of the article")
parser.add_argument("--date", default="20260301", help="Dump date (default: 20260301)")
parser.add_argument("--model", default="es_core_news_md", choices=["es_core_news_md", "es_core_news_lg", "es_dep_news_trf"], help="spaCy model to use")
args = parser.parse_args()

def fmt_time(seconds: float) -> str:
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    return f"{seconds:.2f}s"

t_total = time.perf_counter()

t0 = time.perf_counter()
index_path = DATA_DIR / f"eswiki-{args.date}-index-ns0-clean.json"
data_path = DATA_DIR / f"eswiki-{args.date}-pages-articles-ns0-clean.json"

if not index_path.exists():
    print(f"Error: Index not found at {index_path}")
    exit(1)

with open(index_path, encoding="utf-8") as f:
    idx = json.load(f)

id_to_pos = {rid: pos for pos, rid in enumerate(idx["ids"])}
pos = id_to_pos.get(args.revision_id)
if pos is None:
    print(f"Error: Revision ID {args.revision_id} not found in index")
    exit(1)
print(f"[TIME] Load index:      {fmt_time(time.perf_counter() - t0)}")

t0 = time.perf_counter()
with open(data_path, encoding="utf-8") as f:
    f.seek(idx["offsets"][pos])
    article = json.loads(f.readline())

text = article.get("text", "")
if not text.strip():
    print(f"Error: Article {args.revision_id} has no text content")
    exit(1)
print(f"[TIME] Load article:    {fmt_time(time.perf_counter() - t0)}")

t0 = time.perf_counter()
MODEL_NAME = args.model
nlp = spacy.load(MODEL_NAME)
nlp.select_pipes(disable=["ner", "lemmatizer", "attribute_ruler"])
print(f"[TIME] Load model:      {fmt_time(time.perf_counter() - t0)}  ({MODEL_NAME})")

t0 = time.perf_counter()
doc = nlp(text)


def is_valid_chunk(chunk) -> bool:
    raw = chunk.text
    text = raw.strip()
    tokens = list(chunk)

    # Discard empty chunks after stripping
    if not text:
        return False

    # Reject if raw text contains newlines or wiki section markers
    if "\n" in raw or "===" in raw:
        return False

    # Reject stray bracket artifacts like "Andorra]"
    if text.endswith("]") or text.endswith(")"):
        return False

    # Reject if starts with punctuation, whitespace, or wiki markup artifacts
    if text[0] in {",", ".", ":", ";", "-", "(", ")", "[", "]", '"', "'", "*", "=", "|", "#"}:
        return False

    # Reject wiki section markers (any amount of = in the text)
    if "==" in text:
        return False

    # Count real tokens (ignore SPACE and PUNCT) to avoid "(space) la casa" counting as 3
    real_tokens = [t for t in tokens if t.pos_ not in {"SPACE", "PUNCT"}]

    # Phrasal noun must have at least 2 real tokens
    if len(real_tokens) < 2:
        return False

    # Reject exactly "determiner + noun/propn" (e.g. "el gato", "la casa")
    # but keep "media naranja" (ADJ + NOUN) or "sentido común" (NOUN + ADJ)
    if len(real_tokens) == 2 and real_tokens[0].pos_ == "DET":
        return False

    # Must have at least one token that is not purely functional (DET, PUNCT, SPACE, SYM)
    if not any(t.pos_ not in {"DET", "PUNCT", "SPACE", "SYM"} for t in tokens):
        return False

    # Must have at least one content token longer than 2 chars
    if not any(len(t.text) > 2 and t.pos_ not in {"DET", "PUNCT", "SPACE", "SYM", "ADJ"} for t in tokens):
        return False

    return True


chunks = []
for chunk in doc.noun_chunks:
    if is_valid_chunk(chunk):
        chunks.append({"text": chunk.text.strip(), "root": chunk.root.text, "root_pos": chunk.root.pos_})

print(f"[TIME] Process text:   {fmt_time(time.perf_counter() - t0)}")

t0 = time.perf_counter()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
output_path = OUTPUT_DIR / f"{args.revision_id}_{MODEL_NAME}.json"

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(chunks, f, indent=2, ensure_ascii=False)
print(f"[TIME] Save output:     {fmt_time(time.perf_counter() - t0)}")

print(f"\nExtracted {len(chunks)} phrasal nouns from article {args.revision_id} ({article.get('title', '?')})")
print(f"Saved to: {output_path}")
print(f"[TIME] Total:           {fmt_time(time.perf_counter() - t_total)}")