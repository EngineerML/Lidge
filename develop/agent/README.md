# Agent scaffold

`agent.py` is a single-file, general-purpose tool-using agent that follows the Ridges agent
contract (`research/docs/official/pages/guides_agent-contract.md`):

- `agent_main({"problem_statement": ...}) -> str` returns a unified diff of the working directory.
- Inference: `POST $SANDBOX_PROXY_URL/api/v1/chat/completions` with `Authorization: Bearer $OPENROUTER_API_KEY`
  (the proxy rejects requests without it), non-streaming, fields limited to the proxy's allowlist.
- Stops starting model calls at 90% of `RIDGES_MAX_COST_USD` or on the proxy's budget `429`, and
  keeps a time reserve before `AGENT_TIMEOUT`; whatever is in the working directory then becomes
  the patch.
- The diff is taken against a baseline in a private git dir, so it works in non-git containers and
  never touches a repo's own `.git`. Files the agent wrote are force-added even if `.gitignore`d.
- Tools: `bash`, `read_file`, `write_file`, `replace_in_file`, `finish`. Paths are confined to the
  working directory.
- stdlib + `requests` only (both allowed by `miners/baseline-requirements.txt`).

The prompt is deliberately generic: no task-type routing and no mention of how work is graded
(both are pre-screening rejections; see the participation rules and the Problem Solving page).

## Test

```bash
VIRTUAL_ENV=.venv uv pip install pytest requests
.venv/bin/python -m pytest -q develop/agent/tests      # offline, fake proxy, no spend
```

## Next steps

- Pick the model: `MODEL` (override locally with `RIDGES_AGENT_MODEL`). The proxy forces
  OpenRouter `zdr: true`, so the model needs a zero-data-retention provider; confirm the slug and
  its price on OpenRouter before relying on it.
- Run against real tasks with an OpenRouter key: `ridges miner setup`, then
  `ridges miner run-local --task-path research/repos/ridges-bench/<date>/<task> --agent-path develop/agent/agent.py`.
- Measure score and cost per task across ridges-bench, then compare with the live bars from
  `develop/incentive` (e.g. SN30: >= 0.426, or >= 0.414 at <= $0.146/problem).
