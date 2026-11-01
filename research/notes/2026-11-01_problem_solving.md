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

## Task format

Harbor task: `instruction.md` (the problem statement), `task.toml` (agent/verifier timeouts,
resources), `environment/Dockerfile`, hidden `tests/`, reference `solution/`. No public Problem
Solving samples; `repos/ridges-bench` has samples in the same format from other niches.
