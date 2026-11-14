#!/usr/bin/env bash
# Mirrors data between S3 and data/ (AGENTS.md §8.7). Never deletes anything.
#   down: raw, processed, scenarios   S3 → data/
#   up:   processed, scenarios        data/ → S3   (raw is written only by the cache and the recorder)
set -euo pipefail

direction="${1:-}"
if [ -z "${FLOW_BUCKET:-}" ]; then
  echo "FLOW_BUCKET is not set (put the flow-data BucketName output into .env)." >&2
  exit 1
fi

case "$direction" in
  down)
    for prefix in raw processed scenarios; do
      aws s3 sync "s3://$FLOW_BUCKET/$prefix" "data/$prefix" --only-show-errors
      echo "down: $prefix"
    done
    ;;
  up)
    for prefix in processed scenarios; do
      if [ -d "data/$prefix" ]; then
        aws s3 sync "data/$prefix" "s3://$FLOW_BUCKET/$prefix" --only-show-errors --exclude ".gitkeep"
        echo "up: $prefix"
      fi
    done
    ;;
  *)
    echo "usage: data_sync.sh down|up" >&2
    exit 2
    ;;
esac
