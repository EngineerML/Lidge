# Coding-agent research and how to improve on kaito (2026-11-01)

Goal: an SN30 (Problem Solving) agent that reaches >= 16/29 by 3-validator consensus at
<= ~$0.17/problem. Baseline: kaito (10/29, $0.141), see `2026-11-01_kaito.md`.

Most sources below were read as abstracts, blog posts or secondary summaries, not full papers.
Treat the numbers as directional; nothing here has been reproduced on Ridges tasks yet.

## What the literature says

| # | Finding | Source |
|---|---|---|
| 1 | The harness matters as much as the model: the same model ranks very differently in different harnesses; one orchestration-only change took Gemini 3.1 Pro from 55% to 80.2% on Terminal-Bench 2.0 | Terminal-Bench 2.0 leaderboards; Tensorlake on ForgeCode |
| 2 | Context management mainly helps by preventing context overflow; rule-based elision of old output before LLM summarization was the most efficient strategy; making elided content recoverable bought nothing | Empirical Study of Harness Design (arXiv 2609.20804) |
| 3 | Planning is an accuracy aid for weaker models and mostly a cost saver for strong ones; bash-capable models do fine with bash plus few tools at lower cost | same; execute_code restriction study (arXiv 2607.10569) |
| 4 | Top Terminal-Bench harnesses: environment facts as shell-like output at the start, short default command timeouts (opt in to long ones), background jobs tracked, a plan/todo reminder placed at the end of context, minimal tools with simple schemas, per-model edit formats | Factory Droid write-up; ForgeCode write-up |
| 5 | Lowering per-call error rates compounds into task success ("multiplicative gains"); careful tool descriptions; exact-match string replacement is the most reliable edit | Factory; Anthropic SWE-bench scaffold post |
| 6 | Failures usually start in the first few steps, come from epistemic errors (wrong understanding), and stay hidden until recovery is impossible: validate early, not only at the end | Failure as a Process (arXiv 2607.09510) |
| 7 | Agents find relevant information and then ignore it (Terminal-Bench: solutions found in ~80% of runs, used in 37-50%) | Agents Explore but Agents Ignore (arXiv 2604.17609) |
| 8 | Repeated attempts + selection is the strongest lever: OpenHands best-of-5 60.6 -> 66.4%; critic best-of-8 73.8% vs 57.9% random, and with early stopping only 1.35 attempts on average; SWE-World 55 -> 68 at K=8 | OpenHands blogs; SWE-World (arXiv 2602.03419) |
| 9 | Selection is the bottleneck: CodeMonkeys' oracle over its own candidates is 69.8% vs 57.4% achieved; test-based voting followed by a model-written discriminating test recovers about half the gap at <10% of total cost | CodeMonkeys |
| 10 | Generative yes/no verifiers beat scalar scorers as K grows; generic critics trained on benchmark-style data barely beat random on real outcomes, so prompted judges are a weak selector on their own | SWE-Lego (arXiv 2601.01426); OpenHands critic post |
| 11 | Agents scale badly with more budget unless they are told how much budget is left; a running budget tracker lets them plan and verify accordingly | Budget-Aware Tool-Use / BATS (arXiv 2511.17006) |
| 12 | Consistency is much lower than pass@1: tau-bench 60% pass@1 vs ~25% over repeated trials; two runs of the same SWE-bench setup flipped 53/500 verdicts | ReliabilityBench (arXiv 2601.06112); LayerLens |

## Why reliability is the main lever on Ridges

A task counts only if all three validators solve it. If one run solves a task with probability p,
consensus is roughly p^3 (less if runs are correlated, e.g. by the per-problem seed the proxy may
inject). Raising p from 0.6 to 0.7 raises p^3 from 0.22 to 0.34, so a gain in per-run
reliability is about tripled in the score. ErPing's earlier agent: 14-15 per validator, 12 by
consensus. Variance reduction and selection (#8-#12) map directly onto this.

## Where kaito already follows the literature

Environment survey at the start (#4), files containing the task's rare words, exact-replace edits
and syntax checks (#5), background jobs, time left appended to every tool result, cache marks,
rule-based compaction at 220k tokens (#2), a self-review gate at finish, a careful patch builder.

## Improvements, ranked by expected value per dollar

All of these are general behaviour, not task-type routing (forbidden in Problem Solving), and the
prompts must still never mention grading, hidden tests or the sandbox.

1. **Up-front deliverable contract plus early check (#6, #4).** Before building, have the model
   write a short contract to scratch: output path(s), exact format, every stated constraint, every
   worked example; then write an executable acceptance check (`check.sh` or `check.py` under
   `/tmp/work`) that tests what can be tested (file exists, parses, examples reproduce, timing).
   Re-inject the contract as a short reminder at the end of context every few steps (Droid's
   plan-at-the-end trick), instead of only at finish. Cost: ~1-2 extra calls.
2. **Second attempt with selection, stopped early when not needed (#8, #9, #10).** Use the
   ~$0.15/problem headroom (kaito spends $0.14 of $0.29; leaders $0.16-0.17):
   - Attempt A as now. Then save its diff, restore the tree (kaito's `Tree.restore` already
     does this) and run attempt B from a fresh context with only the contract.
   - Skip B (early stop) when A passed its own acceptance check and the reviewer pass (item 3)
     found nothing, and/or when time or budget left is below what A used.
   - Select: run both acceptance checks on both candidates; when both pass and the deliverables
     agree (same answer file, same outputs on the examples), take either; when they disagree,
     write one discriminating check (CodeMonkeys) or ask a yes/no verifier per candidate (#10).
   - Agreement between two independent attempts is also a confidence signal for answer-type tasks.
   Budget it explicitly: A <= ~55% of the cap, B and selection with the rest.
3. **Enable an independent reviewer, cheaply (#10, kaito's disabled advisor).** A fresh-context call
   with a cheaper model that sees the task, the contract, the diff and the check output, and
   returns a list of concrete problems. Use it to find things to check, not as an accept/reject
   oracle. ~$0.005-0.02 per problem.
4. **Show remaining budget, not just time (#11).** Append "[time left / budget left]" to tool
   results, and scale behaviour: below ~30% left, stop exploring and secure the deliverable.
5. **Cheaper steps -> more steps (#2, CodeMonkeys cost breakdown).** Elide old tool output
   earlier (e.g. outputs older than ~10 steps beyond 600 chars), not only at 220k tokens; context
   re-reads dominate cost. Keep the task, the contract and the last N steps verbatim.
6. **Short default command timeout (#4).** kaito defaults to 120 s; use ~30-60 s, require opting
   in to longer or background, and report runtime only when it is long.
7. **"Use what you found" nudge (#7).** After exploration, ask the model to list what it found that
   changes the plan (existing scripts, docs, tests, reference data) before building.
8. **Model and effort choice by measurement (#1, #3).** Compare the main model at medium vs high
   reasoning on the planning/first step, and a cheaper model for attempt B or the reviewer, on a
   local task set; per-model edit formats if a model misuses `edit_file`.

Expected order of impact: 2 > 1 > 3 > 4 = 5 > 6 > 7; 8 is a tuning pass once the harness is fixed.

## Constraints and risks

- **Originality:** copying is prohibited, and three 99.9% copies of kaito earn nothing. Build our
  own agent (develop/agent) that uses these ideas, and use kaito as a reference, not a base file.
- **Cost cap:** the proxy returns 429 at `RIDGES_MAX_COST_USD`; a second attempt must be
  budgeted, and the first attempt's patch must survive a budget cut.
- **Time:** observed validator runs take up to ~21 min per task; two attempts must fit in
  `AGENT_TIMEOUT` with a reserve for building the patch.
- **Seeds:** if the proxy injects the same per-problem seed for every validator, run-to-run
  differences come from timing and serving; item 2 still helps because B uses a different context.
- **Unverified:** none of this is measured on Ridges tasks. A local loop (N tasks x 3 runs,
  all-3-pass, $/task) is needed to accept or drop each item.

## Sources

- Empirical Study of Harness Design for Coding Agents: https://arxiv.org/abs/2609.20804
- When Does Restricting a Coding Agent to execute_code Help?: https://arxiv.org/abs/2607.10569
- SWE-World: https://arxiv.org/abs/2602.03419
- SWE-Lego: https://arxiv.org/pdf/2601.01426
- Budget-Aware Tool-Use Enables Effective Agent Scaling: https://arxiv.org/abs/2511.17006
- Failure as a Process (CLI agent trajectories): https://arxiv.org/abs/2607.09510
- Agents Explore but Agents Ignore: https://arxiv.org/abs/2604.17609
- Terminal-Bench 2.0: https://arxiv.org/abs/2601.11868, https://www.morphllm.com/terminal-bench-2
- Factory Droid on Terminal-Bench: https://factory.com/news/terminal-bench
- ForgeCode on Terminal-Bench: https://tensorlake.ai/blog/forgecode-terminal-bench
- CodeMonkeys: https://scalingintelligence.stanford.edu/blogs/codemonkeys
- Anthropic SWE-bench scaffold: https://www.anthropic.com/engineering/swe-bench-sonnet
- OpenHands critic / best-of-N: https://openhands.dev/blog/sota-on-swe-bench-verified-with-inference-time-scaling-and-critic-model, https://openhands.dev/blog/20260305-learning-to-verify-ai-generated-code
- ReliabilityBench: https://arxiv.org/html/2601.06112v1; On the Reliability of Computer Use Agents: https://arxiv.org/pdf/2604.17849
