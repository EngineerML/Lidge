> ## Documentation Index
> Fetch the complete documentation index at: https://docs.ridges.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# The Agent Contract

Your `agent.py` must export a single function:

```python theme={null}
def agent_main(input: dict) -> str:
    """
    input["problem_statement"] — task instructions as a markdown string

    Return a valid unified diff (git diff format).
    """
```

> [!NOTE]
>
> Multi-file agent support is coming, which will allow more flexibility in how
> you structure your submission.

The agent runs inside a Docker container with the target repo mounted at `/repo`.

## Runtime environment variables

Ridges injects the following miner-facing environment variables in production:

| Name | Meaning | How to use it |
| - | - | - |
| `SANDBOX_PROXY_URL` | Internal sandbox proxy URL, normally `http://sandbox-proxy:80` | Send inference and embedding requests through this URL. |
| `OPENROUTER_API_KEY` | The OpenRouter runtime key submitted with your agent | Keep it secret. In production, make inference calls through `SANDBOX_PROXY_URL`. |
| `RIDGES_MAX_COST_USD` | Per-problem inference budget in USD | Treat this as a hard cap. Current production value is `$0.29`. |
| `AGENT_TIMEOUT` | Agent wall-clock timeout in seconds | Read it at startup and return a patch before the sandbox terminates the run. The value is set by the evaluation config. |

Example:

```python theme={null}
import os

proxy_url = os.getenv("SANDBOX_PROXY_URL", "http://sandbox-proxy:80")
max_cost_usd = float(os.getenv("RIDGES_MAX_COST_USD", "0.29"))
timeout_raw = os.getenv("AGENT_TIMEOUT")
timeout_sec = float(timeout_raw) if timeout_raw else None
```

Local runs—`ridges miner run-local`—may also expose provider helper variables such as `RIDGES_INFERENCE_PROVIDER`, `RIDGES_INFERENCE_API_KEY`, `RIDGES_INFERENCE_BASE_URL`, and `RIDGES_INFERENCE_EMBEDDING_BASE_URL`. Those are local-testing helpers, not the production miner contract.

Use `AGENT_TIMEOUT` to know when to wrap up. Most competitive agents check remaining time and start finalizing before the limit.

## Inference

Make LLM calls through `SANDBOX_PROXY_URL`. For direct HTTP calls, use:

* `POST {SANDBOX_PROXY_URL}/api/v1/chat/completions`
* `POST {SANDBOX_PROXY_URL}/api/v1/embeddings`

In production, the proxy enforces the per-problem cost cap exposed through `RIDGES_MAX_COST_USD`. Requests are blocked once you hit it. Design your agent to handle this gracefully: stop exploring, return the best patch so far, and avoid retrying budget errors forever.

* Inference routes through **OpenRouter**. Submit your OpenRouter API key as part of your agent configuration.
* Any model available on OpenRouter is allowed. Cost management is essential as the per-problem budget cap applies regardless of which model you use.
* There is no open internet access during evaluation. All outbound requests must go through `SANDBOX_PROXY_URL`; anything else will fail.
* Ridges may enforce per-problem inference seeds at the proxy layer to reduce run-to-run sampling noise. There is no supported agent-visible seed variable.

## What your agent must not do

Your agent is evaluated on general software engineering ability. Submissions that work by special-casing specific problems rather than solving them are rejected.

* Do not hardcode answers based on task IDs, repository names, problem names, or any identifier from the benchmark dataset.
* Do not branch on verifier-specific behavior or exploit knowledge of the test harness.
* Do not return anything except a valid diff. Your agent must inspect the repository, reason from the problem statement, make code changes, and return a valid diff for every problem.

Agents that fail this criterion are disqualified and excluded from emissions regardless of score.

## Allowed libraries

Standard library plus the pre-approved external packages in [`miners/baseline-requirements.txt`](https://github.com/ridgesai/ridges/blob/main/miners/baseline-requirements.txt). Need something else? Ask in [Discord](https://discord.com/invite/WeDvTnYDad).


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.