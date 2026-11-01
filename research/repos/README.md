# Upstream repositories (github.com/ridgesai)

Git submodules pinned at the commit inspected on 2026-11-01. `git submodule update --init` to fetch.

| Repo | What it is |
|---|---|
| `ridges` | The subnet: platform API (`api/`), validator (`validator/`), Harbor runtime (`ridges_harbor/`), miner CLI (`miners/`), incentive math (`utils/incentives.py`, `api/incentives.py`). |
| `ridges-bench` | Sample Harbor tasks (db-engineering, test-generation, dated SWE samples) for local runs. Not used for scoring. |
| `sandbox-proxy` | Inference proxy inside the eval sandbox: OpenRouter routing and the per-problem cost cap. |
| `ridgeline_mcp` | MCP server for Ridgeline, the paid product built on top of winning agents. |
| `abstract-agent-runner` | Older framework for running agents on Polyglot / SWE-Bench (2025). |
| `cave` | Older local-subnet dashboard (2025). |

Third-party code: read it, do not commit changes into these paths.
