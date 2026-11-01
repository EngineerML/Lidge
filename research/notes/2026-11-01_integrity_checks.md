# Copy, hardcoding and integrity checks in the Ridges code (2026-11-01)

Source: `repos/ridges` @ 8b1016cc, `repos/sandbox-proxy` @ 93819666. Validators do not judge
code: every originality and hardcoding decision is made on the platform. The two LLM judges run in
separate worker services that are **not in the public repo**; only their inputs, outputs and the
surrounding workflow are visible.

## The checks, in order

| # | Stage | Where | What is checked | Outcome |
|---|---|---|---|---|
| 1 | Upload | `api/src/utils/upload_agent_helpers.py` | `.py` file, <= 2 MB, hotkey registered, coldkey not banned, signature, 12 h cooldown per competition, paid ticket/burn | HTTP error, no agent created |
| 2 | Upload | `api/src/utils/openrouter_validation.py` | OpenRouter runtime key + management key; workspace must have observability/IO logging and data sharing off | upload rejected |
| 3 | Upload | `queries/agent.py` (~L705) | **exact SHA-256 of the file** against every agent already in the same competition | if equal: synthetic pre-screening **fail**, `duplicate_source`, no judge call, fee kept |
| 4 | Pre-screening | external judge worker; results in `pre_screening_results` | LLM review of source and prompts against the competition's `hardcoding_policy_version` | `pass` / `fail` / `needs_review` with confidence, categories, evidence, `static_findings` |
| 5 | Human review | Discord thread (`discord_*`, `reviewer_id` columns) | `needs_review` cases | human sets pass or fail |
| 6 | Screeners, validators | Harbor runtime, sandbox proxy | runs only; see "Sandbox" below | score |
| 7 | Approval | external judge worker; `approval_jobs` + `approval_job_rounds` | **several rounds, each with its own model**, verdict + approval score + confidence + evidence, aggregated; input = source file, per-validator scores, consensus score, pre-screening verdict and summary | `approved` / `rejected` / `needs_review` (-> human) |
| 8 | Approval | `queries/approval.py:_insert_incentive_approval` | coldkey not banned; still beats the leader by 3% score or 6% cost at decision time | rejected with a reason, or reward score stored |
| 9 | Any time | admin endpoints `/admin/banned-coldkeys` | ban | the coldkey's agents leave leader selection and emissions, accrued score included |

## What this means for copying and adapting

- **Only byte-identical files are caught mechanically.** There is no AST, token or embedding
  similarity check in the code. The upload docstring still says "Pass similarity validation to
  prevent copying", but the AST checker (`code_checks.py`) was deleted on 2025-11-13 (commit
  ba7f3d04, "Remove unneeded auth and code checks"); even then it only checked for `agent_main` and
  base64/zlib decoders.
- **Everything else is judged by LLMs and humans** whose prompts and policy text are private.
  The approval judge sees the full source plus the scores, and the participation rules forbid
  "direct copying without substantive transformation". Assume a near-copy of public code (kaito,
  wren...) can be flagged at pre-screening or approval even if a single byte differs.
- **Copies also fail economically:** a copy scores about what the original scores, and an equal
  score never qualifies (3% / 6% thresholds), so the fee is lost.
- **Obfuscation is self-defeating:** encoded payloads are rejected, and code the judge cannot read
  is held for human review.
- Practical rule: write our own agent; use public agents to learn ideas, not as text to edit.

## Sandbox and runtime limits (validator side)

- No internet: only the sandbox proxy (`SANDBOX_PROXY_URL`); outbound traffic is cut by iptables.
- The proxy accepts only the uploaded runtime key (SHA-256 match), re-checks the OpenRouter
  workspace privacy flags on calls, enforces the per-run cost cap (429), filters request fields to
  an allowlist, can restrict models (`RESTRICTED_MODELS`), forces `stream: false`, and sets
  provider `zdr: true`.
- **Seed:** the proxy overwrites every request's `seed` with `INFERENCE_SEED`, and Harbor derives
  it as `sha256(problem_name) % 2^31` (`ridges_harbor/seed.py`). Every validator and every agent
  gets the same seed on the same problem.
  - Consequence 1: run-to-run variation across the 3 validators comes only from provider-side
    nondeterminism, timing and environment, not from sampling seeds.
  - Consequence 2: inside one run, repeating an identical request yields (near-)identical output;
    a second attempt must differ in its prompt or context to be independent.
- Problem names are hidden behind HMAC aliases (`utils/problem_alias.py`); test names, logs and
  inference payloads are not shown to miners.
