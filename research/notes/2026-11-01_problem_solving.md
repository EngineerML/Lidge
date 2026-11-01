# Problem Solving (SN30) in detail (2026-11-01)

Sources: `docs/official/pages/competitions_problem-solving.md`, `GET /evaluation-sets/30`,
`GET /retrieval/evaluations-for-agent` for the leader ErPing (930bf2b1), `live/2026-11-01/leaderboard_30.json`.

## Problem counts per evaluation (leader's runs)

| Stage | Problems | Leader solved | Pass threshold |
|---|---|---|---|
| Screener 1 | 10 | 5 | 0.30 |
| Screener 2 | 11 | 5 | 0.09 |
| Validator (x3) | 29 each, same 29 | 15 / 14 / 15 | - |
| Consensus (solved by all 3) | 29 | **12 -> 0.4138** | must beat leader |

- Scores are multiples of 1/29: 0.345 = 10/29, 0.379 = 11/29, 0.414 = 12/29. One problem is
  +8.3% relative to 12/29, so beating the leader on score means **13/29 (0.448)**. At the 12/29
  tie, only the cost route (>= 6% cheaper) works; 4 agents tie ErPing at 0.414 and were not approved.
- Variance is expensive: each validator individually solved 14-15, consensus kept 12.
- Problem identities are hidden (aliases like `C6VLW`), `test_results` are empty for miners;
  per-problem cost and timestamps are visible. All problems carry `benchmark_family = problem_solving`.
- Leader cost: about $4.5 per 29-problem validator run (~$0.155/problem); longest run ~21 min.
- A platform restart errored 4 screener runs; the evaluation was re-run automatically.

## Funnel (271 uploads, 174 miners)

pre-screening 261 (3.7% rejected as hardcoded) -> screener 1 239 -> screener 2 237 -> validator 63 -> approved 5.
Average validator score 0.30, best 0.414.

## Ties

A 12/29 tie with the leader gives `performance_delta = 0`, so only the cost route can qualify:
score >= leader and >= 6% cheaper (today <= $0.1463/problem). Then S0 = cost units x multiplier,
e.g. 10% cheaper = 1.7 units. Vcitory, Victory and Firefly tie ErPing at 0.414 but cost more
($0.162-0.171), so they earn nothing. The leader is read at approval time, not upload time.

## Released code

`GET /retrieval/agent-code` hides code at or above `min(10th agent's score, 3rd distinct score)`
(`queries/agent.py:get_code_hiding_score_cutoff`, `CODE_HIDE_TOP_AGENT_COUNT=10`,
`CODE_HIDE_TOP_SCORE_COUNT=3`); everything below is public, including ended competitions.
`tools/fetch_released.sh` downloads it into `released/` (code git-ignored, metadata kept).

- SN30 cutoff today is 11/29: ranks 1-15 hidden, 10/29 agents public.
- **kaito** (the benchmark-phase winner holding ~64% of SN30's share) is public: ~1,600 lines,
  `openai/gpt-6.1-sol` with fallbacks `openai/gpt-6-luna`, `anthropic/claude-haiku-5.5`; tools
  bash, bash_poll, write_file, edit_file, view_file, finish; optional advisor/reviewer prompts;
  90% wall-clock and 85% budget shares.
- wren, sundial, saffron are 99.9% line-identical to kaito at the same score and earn nothing.
- SN29 public agents (0.48-0.50) use `openai/gpt-5.6-luna` / `gpt-6-luna`; SN28 top 20 all hidden;
  ended Linting (27) ranks 13+ public.

## Practice tasks

- `repos/ridges-bench`: Harbor samples (dated SWE, db-engineering, test-generation) with tests and
  a reference solution.
- `ridges miner run-local --dataset aider-polyglot@1.0` or `swebench-verified@1.0`: Harbor
  registry datasets the CLI recommends.
- No Problem Solving samples are published.

## Task format

Harbor task: `instruction.md` (the problem statement), `task.toml` (agent/verifier timeouts,
resources), `environment/Dockerfile`, hidden `tests/`, reference `solution/`. No public Problem
Solving samples; `repos/ridges-bench` has samples in the same format from other niches.
