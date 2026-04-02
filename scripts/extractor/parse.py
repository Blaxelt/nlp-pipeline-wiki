import psycopg
import wikitextparser as wtp
import xml.etree.ElementTree as ET
import time
import os
from pathlib import Path

FILEPATH = Path(__file__).parent / 'eswiki-20260201-pages-articles-multistream1.xml-p1p159400'

def get_plain_text(revision, ns):
    text_element = revision.find(f'{ns}text')
    if text_element is None or text_element.text is None:
        return None
    parsed = wtp.parse(text_element.text)
    references = parsed.get_tags('ref')
    for ref in references:
        ref.contents = ''
    return parsed.plain_text().strip()

def process_all_pages(filepath, conn):
    total_pages = 0
    skipped = 0

    # Use iterparse for memory-efficient XML processing
    context = ET.iterparse(filepath, events=('start', 'end'))
    context = iter(context)
    event, root = next(context)
    ns = root.tag.split('}')[0] + '}'

    batch = []
    BATCH_SIZE = 500

    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pages (
                id TEXT PRIMARY KEY,
                title TEXT,
                text TEXT,
                status TEXT DEFAULT 'pending'
            )
        """)
        conn.commit()

        for event, elem in context:
            if event == 'end' and elem.tag == f'{ns}page':
                title_el = elem.find(f'{ns}title')
                revision = elem.find(f'{ns}revision')

                if revision is None:
                    skipped += 1
                else:
                    rev_id_el = revision.find(f'{ns}id')
                    text = get_plain_text(revision, ns)

                    if text is None:
                        skipped += 1
                    else:
                        batch.append((
                            rev_id_el.text if rev_id_el is not None else None,
                            title_el.text if title_el is not None else None,
                            text
                        ))
                        total_pages += 1

                if len(batch) >= BATCH_SIZE:
                    cur.executemany(
                        "INSERT INTO pages (id, title, text) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING",
                        batch
                    )
                    conn.commit()
                    batch.clear()
                    print(f"  Inserted {total_pages} pages so far...")

                elem.clear()
                root.clear()

        # Insert remaining records
        if batch:
            cur.executemany(
                "INSERT INTO pages (id, title, text) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING",
                batch
            )
            conn.commit()

    return total_pages, skipped

def print_stats(start_time, total_pages, skipped, input_path):
    elapsed_sec  = time.time() - start_time
    elapsed_hour = elapsed_sec / 3600
    pages_hour   = total_pages / elapsed_hour if elapsed_hour > 0 else 0
    input_mb     = os.path.getsize(input_path) / 1024 / 1024

    print("\n========== STATS ==========")
    print(f"Pages processed  : {total_pages}")
    print(f"Pages skipped    : {skipped}")
    print(f"Time elapsed     : {elapsed_sec:.2f} seconds")
    print(f"Speed            : {pages_hour:,.0f} pages/hour")
    print(f"Input file size  : {input_mb:.2f} MB")
    print("===========================\n")

def run(filepath):
    if not filepath.exists():
        print(f"Error: file not found → {filepath}")
        exit(1)

    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://tfm:tfm@localhost/articles")
    
    start_time = time.time()

    with psycopg.connect(DATABASE_URL) as conn:
        total_pages, skipped = process_all_pages(filepath, conn)

    print_stats(start_time, total_pages, skipped, filepath)


if __name__ == "__main__":
    run(FILEPATH)