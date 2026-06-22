#!/bin/sh
set -e

# Ensure persistence directories exist
mkdir -p /data/token_frequencies
mkdir -p /data/frequency/phrasal_nouns
mkdir -p /index

# Seed single-word token-frequency neologisms data if not already present.
TOKEN_FREQ_FILE="/data/token_frequencies/eswiki_neologisms_occurrences_clean_spacy_enriched.json"
if [ ! -f "$TOKEN_FREQ_FILE" ]; then
    echo "Seeding token-frequency neologisms data into /data/token_frequencies/ ..."
    cp /app/data/neologisms/eswiki_neologisms_occurrences_clean_spacy_enriched.json /data/token_frequencies/
fi

# Seed phrasal nouns enriched data if not already present.
PHRASAL_FILE="/data/frequency/phrasal_nouns/eswiki_neologisms_phrasal_nouns_occurrences_enriched.json"
if [ ! -f "$PHRASAL_FILE" ]; then
    echo "Seeding phrasal nouns neologisms data into /data/frequency/phrasal_nouns/ ..."
    cp /app/data/neologisms/eswiki_neologisms_phrasal_nouns_occurrences_enriched.json /data/frequency/phrasal_nouns/
fi

# Ensure the reviews file exists so writes are persisted from the very first review.
if [ ! -f /data/neologism_reviews.json ]; then
    echo "Creating empty /data/neologism_reviews.json ..."
    echo '{}' > /data/neologism_reviews.json
fi

# Make everything world-read/write so the host user can access files
# even though the container may run as root.
chmod -R a+rw /data /index 2>/dev/null || true

exec "$@"
