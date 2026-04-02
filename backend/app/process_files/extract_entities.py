from urllib.parse import quote


def extract_entities(parsed) -> list[dict]:
    """Extract wikilink entities from a parsed wikitext object."""
    entities = []

    for link in parsed.wikilinks:
        surface = link.text if link.text else link.title
        title = link.title
        if not surface or not title:
            continue

        url = (
            "https://es.wikipedia.org/wiki/"
            + quote(str(title).replace(" ", "_"), safe=":/")
        )
        entities.append({"text": str(surface), "title": str(title), "url": url})

    return entities