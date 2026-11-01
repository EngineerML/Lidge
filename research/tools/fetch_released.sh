#!/usr/bin/env bash
# Download public agent code for the top-ranked agents of each competition from a live snapshot.
# Code above the platform's hiding cutoff returns 403 and is recorded as hidden.
# Downloaded code is untrusted: read it, never run it. agent.py files are git-ignored.
# Usage: bash research/tools/fetch_released.sh research/live/<date> [top_n] [set_id ...]
set -uo pipefail
cd "$(dirname "$0")/.."
live=${1#research/}; top=${2:-20}; shift 2 2>/dev/null || shift $#
sets=${*:-30 29 28 27}
API=https://agent-upload.ridges.ai
for s in $sets; do
  python3 -I -c '
import json,sys
for x in json.load(open(sys.argv[1]))["items"][:int(sys.argv[2])]:
    st=x["competition_state"]
    if st["final_score"] is None: continue
    print(x["agent_id"], st["rank"], round(st["final_score"],4), x["version_num"], x["name"].replace(" ","_").replace("/","_"))
' "$live/leaderboard_$s.json" "$top" | while read -r id rank score ver name; do
    out="released/set$s/$(printf '%03d' "$rank")_${name}_v${ver}_${id:0:8}"
    [ -e "$out/agent.py" ] || [ -e "$out/HIDDEN" ] && continue
    mkdir -p "$out"
    printf '{"agent_id":"%s","set_id":%s,"rank":%s,"final_score":%s,"version_num":%s,"name":"%s"}\n' "$id" "$s" "$rank" "$score" "$ver" "$name" > "$out/release.json"
    for wait in 2 5 15 30 60; do
      sleep 1.5
      code=$(curl -sS -m 60 -o "$out/raw" -w '%{http_code}' "$API/retrieval/agent-code?agent_id=$id")
      [ "$code" = 429 ] || [ "$code" = 000 ] || break
      sleep "$wait"
    done
    if [ "$code" = 200 ]; then
      python3 -I -c 'import json,sys; t=open(sys.argv[1]).read(); open(sys.argv[2],"w").write(json.loads(t) if t.startswith("\"") else t)' "$out/raw" "$out/agent.py"
      echo "ok     set$s rank $rank $score $name ($(wc -c < "$out/agent.py") B)"
    else
      echo "$code $(head -c 200 "$out/raw")" > "$out/HIDDEN"; echo "hidden set$s rank $rank $score $name ($code)"
    fi
    rm -f "$out/raw"
  done
done
