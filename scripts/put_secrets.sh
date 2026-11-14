#!/usr/bin/env bash
# Stores API keys in SSM Parameter Store as SecureString (AGENTS.md §8.3).
# Input is hidden and never printed. Press Enter to skip a key.
set -euo pipefail

PREFIX="${FLOW_PARAM_PREFIX:-/flow}"
NAMES=(
  "oag-key-dev|OAG Flight Info key, dev (laptops, research)"
  "oag-connections-key-dev|OAG Connections key, dev"
  "oag-key-demo|OAG Flight Info key, demo (deployed app only)"
  "oag-connections-key-demo|OAG Connections key, demo"
  "google-routes-key|Google Routes key (Gate Planner)"
)

stored=0
for entry in "${NAMES[@]}"; do
  name="${entry%%|*}"
  label="${entry#*|}"
  printf '%s\n  %s/%s (Enter to skip): ' "$label" "$PREFIX" "$name"
  IFS= read -r -s value || value=""
  printf '\n'
  if [ -z "$value" ]; then
    echo "  skipped"
    continue
  fi
  aws ssm put-parameter --name "$PREFIX/$name" --type SecureString --overwrite \
    --value "$value" --query Version --output text >/dev/null
  echo "  stored"
  stored=$((stored + 1))
  unset value
done
echo "Stored $stored key(s) under $PREFIX/."
