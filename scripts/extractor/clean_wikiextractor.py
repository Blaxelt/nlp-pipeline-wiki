#!/usr/bin/env python3
import json
import sys
import urllib.request

from wikiextractor.extract import Extractor


def get_clean_text(revision_id: str) -> str:
    """Fetch wikitext for the given revision from the Wikipedia API and clean it."""
    api_url = (
        "https://es.wikipedia.org/w/api.php"
        f"?action=query&prop=revisions&revids={revision_id}"
        "&rvprop=content&rvslots=main&format=json"
    )
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

    # Parse wikitext using wikiextractor
    extractor = Extractor(
        id=page.get("pageid", "0"), 
        revid=revision_id, 
        urlbase="https://es.wikipedia.org", 
        title=page.get("title", ""), 
        page=[""]
    )
    paragraphs = extractor.clean_text(wikitext)
    
    # join paragraphs to generate plain text
    return "\n\n".join(paragraphs).strip()


def main():
    if len(sys.argv) < 2:
        print("Usage: python clean_wikiextractor.py <revision_id>")
        sys.exit(1)
        
    revision_id = sys.argv[1]
    print(f"Fetching and cleaning text for revision {revision_id}...")
    
    try:
        clean_text = get_clean_text(revision_id)
        with open("output_wikiextractor.txt", "w", encoding="utf-8") as f:
            f.write(clean_text)
        print("Successfully wrote clean text to output_wikiextractor.txt")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
