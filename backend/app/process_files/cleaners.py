import wikitextparser as wtp
import mwparserfromhell
from wikiextractor.extract import Extractor


def clean_wikitextparser(wikitext: str) -> str:
    parsed = wtp.parse(wikitext)

    for ref in parsed.get_tags("ref"):
        try:
            ref.contents = ""
        except AttributeError:
            pass

    for tpl in parsed.templates:
        try:
            tpl.string = ""
        except Exception:
            pass

    for table in parsed.tables:
        try:
            table.string = ""
        except Exception:
            pass

    for math in parsed.get_tags("math"):
        try:
            math.contents = ""
        except AttributeError:
            pass

    return parsed.plain_text().strip()


def clean_mwparserfromhell(wikitext: str) -> str:
    parsed = mwparserfromhell.parse(wikitext)

    for template in parsed.filter_templates():
        try:
            parsed.remove(template)
        except ValueError:
            pass

    for tag in parsed.filter_tags():
        if tag.tag in ("ref", "math", "table"):
            try:
                parsed.remove(tag)
            except ValueError:
                pass

    for wikilink in parsed.filter_wikilinks():
        title = str(wikilink.title).strip().lower()
        if title.startswith(("archivo:", "imagen:", "file:", "image:", "categoría:", "category:")):
            try:
                parsed.remove(wikilink)
            except ValueError:
                pass

    return parsed.strip_code().strip()


def clean_wikiextractor(wikitext: str, page_id: str = "0", rev_id: str = "0", title: str = "") -> str:
    extractor = Extractor(
        id=page_id,
        revid=rev_id,
        urlbase="https://es.wikipedia.org",
        title=title,
        page=[""],
    )
    paragraphs = extractor.clean_text(wikitext)
    return "\n\n".join(paragraphs).strip()
