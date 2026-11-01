# Ridges (SN62) research

## Layout

```
repos/                 official github.com/ridgesai repos as pinned submodules (see repos/README.md)
docs/official/         snapshot of docs.ridges.ai: llms.txt, llms-full.txt, pages/ (one .md per page),
                       site-llms.txt (www.ridges.ai/llms.txt, the Ridgeline product)
live/YYYY-MM-DD/       raw JSON from the dashboard API (agent-upload.ridges.ai) and chain (btcli/SDK),
                       plus SUMMARY.md
notes/                 findings, one dated file per topic
tools/                 scripts that produce docs/official and live/
```

## Notes

- [Environment and proxy](notes/2026-11-01_environment.md)
- [Mechanism and live state](notes/2026-11-01_mechanism.md)
- [Live summary 2026-11-01](live/2026-11-01/SUMMARY.md)

## Refresh

```bash
git submodule update --init                     # upstream repos
bash research/tools/fetch_docs.sh               # rewrites docs/official
bash research/tools/fetch_live.sh               # writes live/<today>/ (spaced, retries 429s)
# chain data needs proxychains with an http entry; see notes/2026-11-01_environment.md
python3 -I research/tools/summarize.py research/live/<today> > research/live/<today>/SUMMARY.md
```

Dashboard: https://www.ridges.ai/agents (per-competition pages `/agents/<set_id>`).
