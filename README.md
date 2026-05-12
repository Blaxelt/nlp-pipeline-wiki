# MSc thesis project

Web application for reviewing Spanish Wikipedia article extraction and cleaning quality.

## Architecture

**Backend (FastAPI)** - Serves articles from a preprocessed Wikipedia dump. API routes for articles, neologisms, and Wikipedia URL resolution.

**Frontend (React + TypeScript + Vite)** - Routing-based single-page app with two main views.

**NLP Pipeline (Python scripts)** - Set of standalone tools for corpus ingestion, wikitext cleaning, neologism detection, category graph construction, and extraction quality evaluation.

## Functionalities

- **Article review** - Search articles by title or revision ID, navigate the corpus sequentially, view cleaned text alongside the live Wikipedia article in an iframe.
- **Entity extraction** - Fetch live wikitext from the Wikipedia API, parse wikilinks, and display them as clickable highlights in the article text.
- **Cleaner comparison** - Compare the output of three wikitext cleaning libraries (wikitextparser, mwparserfromhell, wikiextractor) side by side with word-level diff.
- **Neologism review** - Browse and filter detected neologisms (words appearing in a new dump snapshot but not in an older one). Filter by frequency, page count, category depth, and review status. Mark neologisms as valid or discarded with optional rationale.
- **Dump loading** - Trigger download and processing of a Wikipedia dump from the UI.
- **Quality evaluation scripts** - Dictionary coverage histograms, category depth analysis, Zipf distribution plots.

## Quick Start
Requires [Docker](https://www.docker.com/).
The easiest way to run the application is with the production Docker Compose file:
1. Download [`docker-compose.prod.yml`](docker-compose.prod.yml) into a folder by itself.
2. Run:
   ```bash
   docker compose -f docker-compose.prod.yml up -d
3. Docker will pull the images and start the containers automatically.
4. Then open http://localhost in your browser.

## References

Original Spanish DBpedia autoupdate pipeline (2020): [github.com/oussama-talaoui/updating-esdbpedia](https://github.com/oussama-talaoui/updating-esdbpedia)
