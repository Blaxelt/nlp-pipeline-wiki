#!/usr/bin/env python3
import json
import re
import sys
import urllib.request

import mwparserfromhell


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

    # Parse wikitext using mwparserfromhell
    parsed = mwparserfromhell.parse(wikitext)
    
    # Remove templates (this includes infoboxes)
    for template in parsed.filter_templates():
        try:
            parsed.remove(template)
        except ValueError:
            pass

    # Remove <ref> tags and <math> equations
    for tag in parsed.filter_tags():
        if tag.tag in ("ref", "math", "table"):
            try:
                parsed.remove(tag)
            except ValueError:
                pass

    # Remove file/image wikilinks (which leave captions behind)
    for wikilink in parsed.filter_wikilinks():
        title = str(wikilink.title).strip().lower()
        if title.startswith(("archivo:", "imagen:", "file:", "image:", "categoría:", "category:")):
            try:
                parsed.remove(wikilink)
            except ValueError:
                pass
    
    # Generate clean text by stripping remaining wikicode
    return parsed.strip_code().strip()


def main():
    if len(sys.argv) < 2:
        print("Usage: python clean_mwparserfromhell.py <revision_id>")
        sys.exit(1)
        
    revision_id = sys.argv[1]
    print(f"Fetching and cleaning text for revision {revision_id}...")
    
    try:
        clean_text = get_clean_text(revision_id)
        with open("output_mwparserfromhell.txt", "w", encoding="utf-8") as f:
            f.write(clean_text)
        print("Successfully wrote clean text to output_mwparserfromhell.txt")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
