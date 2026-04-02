from fastapi import APIRouter
from pydantic import BaseModel
from app.core.wikipedia_index import wikipedia_index

router = APIRouter()

class TitleQuery(BaseModel):
    titles: list[str]
    lang: str = "es"

@router.post("/urls")
def get_urls(query: TitleQuery, description="Get Wikipedia URLs for a list of entities"):
    index = wikipedia_index[query.lang]
    base_url = f"https://{query.lang}.wikipedia.org/wiki/"

    urls = []

    for title in query.titles:
        normalized = title.replace(" ", "_")

        if normalized in index:
            url = base_url + normalized
            urls.append(url)

    return {"urls": urls, "lang": query.lang}