FROM python:3.12-slim

WORKDIR /app

# Bake neologism JSONs into a single clean directory so they survive
# host-mounted /data volume overwrites at runtime.
RUN mkdir -p /app/data/neologisms
COPY data/token_frequencies/eswiki_neologisms_occurrences_clean_spacy_enriched.json /app/data/neologisms/
COPY data/frequency/phrasal_nouns/eswiki_neologisms_phrasal_nouns_occurrences_enriched.json /app/data/neologisms/

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download es_core_news_sm

# Apply patches to installed packages
COPY backend/patches/ /tmp/patches/
RUN apt-get update && apt-get install -y --no-install-recommends patch && \
    cd /usr/local/lib/python3.12/site-packages/wikiextractor && \
    patch -p1 < /tmp/patches/wikiextractor-extract-regex.patch && \
    rm -rf /tmp/patches/ && \
    apt-get purge -y patch && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

COPY backend/app/ app/
COPY backend/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["fastapi", "run", "app/main.py", "--port", "8000"]
