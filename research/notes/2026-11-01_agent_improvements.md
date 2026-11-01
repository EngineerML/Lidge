# How to improve on kaito for SN30 (2026-11-01, revised after full-text reading)

Goal: an SN30 (Problem Solving) agent at >= 16/29 by 3-validator consensus, <= ~$0.17/problem.
Baseline: kaito (10/29, $0.141), see `2026-11-01_kaito.md`. Evidence: `2026-11-01_paper_readings.md`
(16 papers, full text) plus the Factory, ForgeCode, Anthropic and OpenHands write-ups. Nothing here
is measured on Ridges tasks yet. Constraints: `2026-11-01_integrity_checks.md` (own code, no
copying; fixed per-problem seed; no task-type routing; prompts never mention grading).

## What changed after reading the full texts

| Earlier claim (from abstracts/summaries) | Full text says | Effect on the plan |
|---|---|---|
| Best-of-N with a verifier is the strongest lever (OpenHands 73.8 vs 57.9) | That number is on a *mixed-outcome subset*; on the full distribution Best@4 gains are +2.6-3.9; badly trained critics fall below random; at small K verifier choice barely matters | Second attempt drops from #1 to a conditional step |
| Spend compute on more attempts | SWE-Lego: extending one attempt pays first, rollouts only after ~100+ turns | Make attempt 1 longer and better first |
| Prompted judges are weak selectors | Judges reading patches alone lose to test voting (CodeMonkeys), but strong prompted judges with reasoning match trained ones on verdict accuracy (SWE-World), and pairwise beats pointwise (V1) | If we select, use execution evidence + one pairwise judgment run in both orders |
| Tell the agent its budget (BATS) | Confirmed and large: +18.6pp on SWE-bench at equal cost with a numeric used/remaining block + tiers; but prompts alone still overspend 12-33% (INTENT) | Promote to #2 and add a hard guard |
| Failures start early | Quantified: decisive error median step 7, 58% epistemic (false premise 31%, spec neglect 15%); ambiguity is a top source of run-to-run variance | Structured opening becomes #1 |
| tau-bench "60% -> 25%" and "pass@1 overestimates 20-40%" | Cited or unsupported claims in a weak 20-task paper | Dropped |
| Planning tool, summarization, recall | Strong models: cost lever only, no accuracy; recall unused | Skip |

## Plan, ranked by expected effect

1. **Structured opening (epistemic errors, ambiguity, ignored discoveries).** Before the first edit:
   survey (kaito already does it), then "investigate every relevant file you found; do not proceed
   until you have examined the available resources" (best-measured prompt, +4.5 pass@1), then
   write to scratch: deliverables (path, format), every explicit requirement as a checklist,
   assumptions to verify, and candidate interpretations with the repo evidence for each, picking
   the best-supported one (or satisfying several when cheap). Premise checks first: working dir,
   repo root, interpreter/versions, which executables exist (missing executables are the #1
   command failure, 24.1%), how tests run.
2. **Budget and time tracker with a hard guard (BATS, INTENT, LHTB).** Append
   `[budget used $x / remaining $y, time left m:ss]` to every tool result with tiered guidance
   (>=70% explore; 30-70% converge; 10-30% verify and finalize; <10% essentials only). Hard
   guard in code: if projected cost of the next call (last call cost x 1.5) exceeds remaining
   minus a 15-20% reserve, or time is in the reserve, force the finish path. Milestone: a complete
   first version of the deliverable must exist by ~50% of time (timeouts are 79% of long-horizon
   failures; partial-but-valid beats nothing).
3. **Verification gate, constraint by constraint, with fresh evidence (fabrication, weak checks).**
   At finish: re-run the deliverable and checks *now*, map each checklist item to the command
   output that proves it, and treat earlier "tests passed" claims as untrusted (fabrication
   clusters after lock-in). Largest BATS ablation drop came from removing this.
4. **Tool-layer guards (cheap, deterministic, reduce variance).** Show exit code and cwd after
   every command; flag empty output from state-changing commands (cd, build, install); identical-
   call stuck detector (remind after 5, change approach after 8); after ~5 unproductive fix steps
   inject "list your assumptions; which one is unverified?"; when output shows new files or
   errors the model has not referenced, add a one-line "is this relevant?" nudge (+16 interaction);
   cap tool output; auto-retry transient proxy/provider errors.
5. **Conditional second attempt with pairwise selection.** Only when attempt 1 has no passing
   fresh check and >= ~40% budget and time remain. Attempt B starts from a fresh context with the
   checklist and a different framing (the fixed seed makes identical requests repeat). Select by
   execution first: run both candidates' checks plus one agent-written discriminating test; if
   still tied, one pairwise judgment in both orders with rubric questions (incomplete, untested,
   broke other behaviour), reasoning before verdict; default to attempt A or the smaller change
   when the orders disagree. Expect a few points, not oracle-level gains.
6. **Cheaper steps.** Elide bulky old tool outputs at ~60% of a modest effective window (T4 was
   cheapest in 7/8 panels), keep task, checklist and recent turns verbatim. Optional persistent
   Python REPL tool for data/computation work (-25% cost at equal accuracy), keep `edit_file` for
   repo edits (bash-only collapsed one model on SWE).
7. **Model and reasoning effort by measurement.** Higher effort for the opening and the
   verification gate (raised use of discovered information); returns flatten past ~16k thinking
   tokens. One agent, no sub-agents, no cross-task notes.

Skip: recall tools, LLM summarization, a plan tool for accuracy, sub-agents, memory across tasks.

## Why reliability dominates on Ridges

A task counts only if all 3 validator runs solve it (consensus ~p^3). Cross-seed unanimity on
repo tasks was only 74-79% in 2607.10569, and ErPing's earlier agent got 14-15 per validator vs
12 by consensus. Items 1-4 are deterministic habits that reduce variance; they come before
spending budget on a second attempt.

## Constraints and risks

- Originality: build our own agent in `develop/agent`; kaito is a reference for ideas only.
- Cost cap is enforced by the proxy (429); attempt A's patch must survive a cut.
- Validator runs already take up to ~21 min per task; reserves for verification and patch build.
- All gains above come from other benchmarks and models; each item needs the local loop
  (N tasks x 3 runs, all-3-pass, $/task) before it is kept.

## Sources

Papers: see `2026-11-01_paper_readings.md` (arXiv 2609.20804, 2607.10569, 2512.10398, 2501.14723,
2603.03800, 2602.03419, 2601.01426, 2603.04304, 2607.09510, 2604.17609, 2601.06112, 2604.17849,
2601.11868, 2607.08964, 2511.17006, 2602.11541).
Write-ups: https://factory.com/news/terminal-bench, https://tensorlake.ai/blog/forgecode-terminal-bench,
https://www.anthropic.com/engineering/swe-bench-sonnet,
https://openhands.dev/blog/20260305-learning-to-verify-ai-generated-code.
