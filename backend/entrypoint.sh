#!/bin/sh
set -e

# Ensure persistence directories exist
mkdir -p /data/frequency
mkdir -p /index

# Seed the baked neologisms frequency data if the host volume doesn't have it yet.
# This file is baked into the image at /app/baked-data/ so it survives bind mounts.
if [ ! -f /data/frequency/eswiki_neologisms_occurrences_enriched_clean.json ]; then
    echo "Seeding baked neologisms data into /data/frequency/ ..."
    cp /app/baked-data/frequency/eswiki_neologisms_occurrences_enriched_clean.json /data/frequency/
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
