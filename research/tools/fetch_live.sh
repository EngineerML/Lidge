#!/usr/bin/env bash
# Snapshot the public dashboard backend (agent-upload.ridges.ai, read-only GETs) into live/<UTC date>/.
# The API rate-limits (429), so requests are spaced out and retried with backoff.
set -uo pipefail
cd "$(dirname "$0")/.."
API=${RIDGES_API:-https://agent-upload.ridges.ai}
out=live/$(date -u +%F)
mkdir -p "$out"
get() {
  local name=$1 path=$2 code
  [ -s "$out/$name.json" ] && [ "${FORCE:-0}" != 1 ] && { echo "skip $name"; return; }
  for wait in 2 5 15 30 60; do
    sleep 1.5
    code=$(curl -sS -m 60 -o "$out/$name.json" -w '%{http_code}' "$API$path")
    [ "$code" = 200 ] && { echo "ok $name"; return; }
    [ "$code" = 429 ] || [ "$code" = 000 ] || break  # 000: proxy CONNECT also returns 429
    sleep "$wait"
  done
  echo "FAIL $name $path ($code)"; rm -f "$out/$name.json"
}
ids() { python3 -c 'import json,sys;[print(c["set_id"]) for c in json.load(open(sys.argv[1])) if not sys.argv[2:] or c.get("state") in sys.argv[2:]]' "$@"; }

get openapi /openapi.json
get competitions /competitions
get competitions_accepting "/competitions?accepting=true"
get evaluation_sets /evaluation-sets/
get top_agents /retrieval/top-agents
get network_statistics /retrieval/network-statistics
get weights /scoring/weights
get screener_info /scoring/screener-info
get connected_validators /validator/connected-validators-info
for s in screener_1 screener_2 validator; do get "queue_$s" "/retrieval/queue?stage=$s"; done
for id in $(ids "$out/competitions.json"); do
  get "competition_$id" "/competitions/$id"
  get "overview_$id" "/evaluation-sets/$id/overview"
  get "approved_$id" "/evaluation-sets/$id/approved-agents"
  get "leaderboard_$id" "/evaluation-sets/$id/leaderboard?page=1&page_size=100"
  get "network_statistics_$id" "/retrieval/network-statistics?set_id=$id"
  get "eval_pricing_$id" "/upload/eval-pricing?set_id=$id"
done
date -u +%FT%TZ > "$out/FETCHED_AT"
