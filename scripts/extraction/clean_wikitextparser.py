#!/usr/bin/env python3
import json
import sys
import urllib.request

import wikitextparser as wtp


def get_clean_text(revision_id: str) -> str:
    """Fetch wikitext for the given revision from the Wikipedia API and clean it."""
    api_url = (
        "https://es.wikipedia.org/w/api.php"
        f"?action=query&prop=revisions&revids={revision_id}"
        "&rvprop=content&rvslots=main&format=json"
    )
    # Using the same user-agent as seen in the articles.py code to avoid blocks
    req = urllib.request.Request(
        api_url, 
        headers={"User-Agent": "MSc student (b.tluo@alumnos.upm.es) retrieving wikitext for master thesis (educational use)"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        
    pages = data.get("query", {}).get("pages", {})
    if not pages or "-1" in pages:
        raise ValueError(f"Revision {revision_id} not found.")

    page = next(iter(pages.values()))
    if "revisions" not in page:
        raise ValueError(f"No revisions found for revision ID {revision_id}")

    wikitext = page["revisions"][0]["slots"]["main"]["*"]

    # Parse wikitext
    parsed = wtp.parse(wikitext)
    
    # Delete references
    for ref in parsed.get_tags("ref"): 
        try:
            ref.contents = ""
        except AttributeError:
            pass

    # Delete templates (e.g., infoboxes)
    for tpl in parsed.templates:
        try:
            tpl.string = ""
        except Exception:
            pass

    # Delete tables
    for table in parsed.tables:
        try:
            table.string = ""
        except Exception:
            pass

    # Delete math tags
    for math in parsed.get_tags("math"):
        try:
            math.contents = ""
        except AttributeError:
            pass
            
    return parsed.plain_text().strip()


def main():
    if len(sys.argv) < 2:
        print("Usage: python clean_wikitextparser.py <revision_id>")
        sys.exit(1)
        
    revision_id = sys.argv[1]
    print(f"Fetching and cleaning text for revision {revision_id}...")
    
    try:
        clean_text = get_clean_text(revision_id)
        with open("output_wikitextparser.txt", "w", encoding="utf-8") as f:
            f.write(clean_text)
        print("Successfully wrote clean text to output_wikitextparser.txt")
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
