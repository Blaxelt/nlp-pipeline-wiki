import copy
from urllib.parse import quote

# Namespace prefixes that indicate a file/image wikilink (case-insensitive).
# Wikilinks whose title starts with any of these are media embeds, not article links.
_MEDIA_PREFIXES = (
    "archivo:",
    "file:",
    "imagen:",
    "image:",
    "fichero:",
)


def extract_entities(parsed) -> list[dict]:
    """Extract wikilink entities from a parsed wikitext object.

    Wikilinks nested inside file/image embeds (e.g. captions of
    ``[[Archivo:Foo.jpg|miniatura|[[Article|text]]]]``) are excluded because
    they do not appear in the clean plain text.
    """
    # Work on a copy so we don't mutate the caller's parsed object.
    parsed_copy = copy.copy(parsed)

    # Blank out top-level file/image wikilinks so their nested children are
    # invisible to the subsequent iteration.
    for link in parsed_copy.wikilinks:
        try:
            title_str = str(link.title).lower()
        except AttributeError:
            # Malformed wikilink — wikitextparser's internal regex returned None.
            continue
        if title_str.startswith(_MEDIA_PREFIXES):
            try:
                link.string = ""
            except Exception:
                pass

    entities = []
    for link in parsed_copy.wikilinks:
        try:
            title = link.title
        except AttributeError:
            continue
        # Skip remaining media/file references that weren't caught above.
        if not title or str(title).lower().startswith(_MEDIA_PREFIXES):
            continue

        surface = link.text if link.text else title
        if not surface:
            continue

        url = (
            "https://es.wikipedia.org/wiki/"
            + quote(str(title).replace(" ", "_"), safe=":/")
        )
        entities.append({"text": str(surface), "title": str(title), "url": url})

    return entities