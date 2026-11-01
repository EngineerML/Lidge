# Ridges (SN62) mechanism (2026-11-01)

Sources: `docs/official/` snapshot, `repos/ridges` @ 8b1016cc (v0.3.16), `live/2026-11-01/`.
Code references are paths inside `repos/ridges`.

## What a miner submits

One file, `agent.py`, exporting `agent_main(input: dict) -> str`. The Harbor runtime
(`ridges_harbor/ridges_miner_runtime.py`) reads the task's `instruction.md`, calls
`agent_main({"problem_statement": instruction})` inside the task container and writes the returned
string as the patch. Non-string or empty return = runtime failure.

- Only network path: `SANDBOX_PROXY_URL` (`/api/v1/chat/completions`, `/api/v1/embeddings`),
  routed to **OpenRouter with the miner's own key**, submitted with the agent. Any OpenRouter model.
- Per-problem budget `RIDGES_MAX_COST_USD` (docs: $0.29), enforced by the proxy; `AGENT_TIMEOUT`
  is the wall clock. No package index, no web.
- Libraries: stdlib + `miners/baseline-requirements.txt` (requests, httpx, openai, numpy, pandas,
  pytest, tree-sitter, ...).
- The repo-root `agent.py` is a stale stub (old `/api/inference` contract, reads a gold diff); ignore it.

## Pipeline per upload

1. **Pay**: burn alpha. Price per competition starts at $5, x1.149 per upload bought, halves every
   30 min back to the $5 floor (~10 uploads/h steady state). Live: Problem Solving $7.66, others $5.
2. **Cooldown**: one upload per hotkey per competition per 12 h; rejected uploads still count.
3. **Pre-screening**: an automated (LLM) code/prompt review against the participation rules;
   uncertain cases go to a human. Rejects hardcoding, task routing, prompts that recall benchmark
   answers, *any mention of evaluation/hidden tests/sandbox*, obfuscation, duplicates.
   Live reject rate ~4-11% (SN30 10/264, SN29 156/1565, SN28 602/5537).
4. **Screener 1 -> Screener 2** (Ridges-hosted, autoscaled), disjoint problem sets, each with a
   pass threshold (policy per competition; SN30 live: s1 0.30, s2 0.09).
5. **Validators x3** (independent nodes; one may be `platform-validator-1`). Consensus score: a
   problem counts only if **every** assigned validator solved it. Scoring is deterministic: patch is
   applied to a clean copy, hidden tests/reference outputs decide 1/0 per task. Test names and logs
   are never shown; miners see score, cost and runtime only.
6. **Approval** (`queries/approval.py`): compares against the current leader of that competition
   and stores a reward score once. Owner-hotkey baselines (`*-RT` agents, hotkey `5EsNzkZ3...`)
   are approved and can lead, but always get reward score 0.

## Reward score (`utils/incentives.py`)

Qualify if either:

- performance: `(s - s_L) / s_L >= 3%`, or
- cost: `s >= s_L` and `(c_L - c) / c_L >= 6%` (needs leader cost data).

Units (log-compounded, below-threshold fraction still counts once qualified):

    perf_units = ln(1 + dperf) / ln(1.03)          (only if dperf > 0)
    cost_units = min(ln(1 - dcost) / ln(0.94), 1/0.06 ~ 16.7)   (only if dcost > 0)
    S0 = (perf_units + cost_units) * (1 + sqrt(hours_since_leader_approved / 6))

- First approved agent in a set (no leader): `units = 100 * score`, multiplier as computed.
- Benchmark phase winner: `S0 = 100 * score (+ cost units vs leader)`, no time multiplier.
  Benchmark-phase time does not count toward the next multiplier.
- Decay: `S(t) = S0 * 2^(-t / 336h)` (14-day half-life).
- Within a competition, weight_i = S_i / sum S_j over approved agents whose hotkey is still
  registered; then scaled by the competition's `raw_emission_weight`; summed per hotkey.
- Shares not paid out (inactive competition, no eligible agent, sum < 1) go to `OWNER_HOTKEY`
  (`api/incentives.py`), i.e. effectively burned.

Verified against live data: every approved agent's stored `initial_reward_score` equals
`relative_improvement_units * time_multiplier` (see `develop/incentive` tests).

## Weight setting

Validators do **not** score on their own for weights: `validator/background_loops.py` polls
`GET /scoring/weights` from the platform and calls `subtensor.set_weights` with it. On-chain
incentive at block 9409678 matched the platform weights for all 35 paid hotkeys to within 2e-5.
The platform is the source of truth; Yuma consensus just passes it through.

## Live state (2026-11-01 07:40Z)

| set | competition | share | leader score / cost | leader since | multiplier now | approved |
|---|---|---|---|---|---|---|
| 30 | Problem Solving | 0.50 | 0.414 / $0.156 (ErPing) | 10-31 22:59 | 2.20x | 5 |
| 29 | Test Generation | 0.25 | 0.600 / $0.152 (ridgeguard v2) | 10-31 18:02 | 2.51x | 21 |
| 28 | Database Query Eng. | 0.25 | 0.380 / $0.092 (mino v17) | 10-25 01:34 | 4.81x | 15 |

History: SWE+Poly (23, Jun), SWE-Bench (24), Infinite SWE pilot/main (25-26, Jul-Aug),
Linting (27, ended 10-31), then three parallel niches since September. Niches rotate every few
weeks; the newest gets the largest share.

Chain: alpha 0.00839 TAO, market cap ~49k TAO, tempo 360 blocks. Miners received 147.6 alpha in
the last tempo, i.e. ~2.9k alpha/day ~ 24.7 TAO/day across all miners.

### Observations

- **Benchmark-phase winners dominate.** `kaito` won SN30's opening benchmark phase with score
  0.345 -> S0 = 34.5, while the three later, *better* agents got S0 4.7-7.0 (2.9-3.2 units x
  1.6-2.3). kaito holds 64% of SN30's share (0.32 of all miner weight, ~8 TAO/day) at a score below
  the current leader. Being present when a new competition's benchmark phase ends is the single
  biggest payout event.
- **Stalls pay.** SN28's leader is 7 days old: the next >= 3% improvement there gets ~4.8x now and
  ~6.3x after a week. A 1-unit improvement in SN28 now ~ the S0 of a 2-unit improvement in SN30.
- **Cost is a cheap lever.** A 30% cost cut at equal score = 5.8 units, about a 19% score gain.
  Leaders run $0.09-0.16/problem against a $0.29 cap; e.g. Jackpot qualified in SN30 at the same
  score as Apollo by being 17% cheaper.
- **Variance hurts.** 3-validator consensus counts a task only if all three runs solve it, so
  flaky agents lose; deterministic, self-verifying behaviour matters more than peak ability.
- **Screening is cheap to pass, validators are not.** SN30 screener averages 0.55 / 0.42 vs
  validator average 0.40 and leader 0.414; the bar is the leader, not the screeners.
- **Code is not public while it leads** (top agents hidden; code is released when unseated).

## Rules that matter for building

- Write the agent as if for your own codebase; no task recognition, no task-type routing
  (explicitly forbidden in Problem Solving), no prompts mentioning tests being hidden, graders,
  sandbox or scoring; tell it to run the repo's own tests.
- Problem Solving: deliver exactly the requested artifact at the requested path/format, one
  answer, regular files only (no symlinks/submodules), correctness before speed.
- Copies earn nothing: 3%/6% thresholds plus plagiarism and ban rules (a banned coldkey loses
  all accrued reward score).
