#!/usr/bin/env bash
# Snapshot docs.ridges.ai (Mintlify) and www.ridges.ai/llms.txt into docs/official/.
set -euo pipefail
cd "$(dirname "$0")/.."
out=docs/official
mkdir -p "$out/pages"
curl -sSL -m 60 https://docs.ridges.ai/llms.txt -o "$out/llms.txt"
curl -sSL -m 120 https://docs.ridges.ai/llms-full.txt -o "$out/llms-full.txt" || true
curl -sSL -m 60 https://www.ridges.ai/llms.txt -o "$out/site-llms.txt"
grep -oE 'https://docs\.ridges\.ai/[^)]+\.md' "$out/llms.txt" | sort -u | while read -r u; do
  f="$out/pages/$(echo "${u#https://docs.ridges.ai/}" | tr '/' '_')"
  curl -sSL -m 60 "$u" -o "$f" && echo "ok $f"
done
date -u +%FT%TZ > "$out/FETCHED_AT"
