FROM python:3.12-slim

WORKDIR /app

# Bake the neologisms frequency JSON into a non-mounted path so it can be
# copied into the host-mounted /data volume at runtime.
RUN mkdir -p /app/baked-data/frequency
COPY data/frequency/eswiki_neologisms_occurrences_enriched_clean.json /app/baked-data/frequency/

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download es_core_news_sm

COPY backend/app/ app/
COPY backend/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["fastapi", "run", "app/main.py", "--port", "8000"]
