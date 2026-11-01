# Coding-agent papers, full-text readings (2026-11-01)

All 16 papers were retrieved as full text from `arxiv.org/html/<id>` and read to the end
(body, tables, relevant appendices). Caveats: numbers were extracted through a summarizing fetch
or HTML-to-text conversion, so spot-check before quoting; some values exist only in figure
images and are marked as such. Implications assume our setting: single-file agent, ~$0.29/task
cap, ~15-20 min, 3-validator consensus, fixed per-problem seed, no task-type routing, no mention
of grading in prompts.

## Harness design

**2609.20804 Empirical Study of Harness Design.** ReAct harness, Nemotron-3 30B/120B/550B +
Mistral-Medium-3.5-128B, temp 0, SWE-bench Verified (500) + Terminal-Bench 2.1 (89), budgets
32k-128k, 176 settings, *one run each*.
- Context tiers T0 none / T1 elision / T2 +recall / T3 summary / T4 elision at 0.6 then summary at
  0.85: gain over T0 shrinks with window (SWE +35.7pp at 32k, +2.7 at 128k). 550B@128k:
  T0 59.8% $2.08 vs T4 65.8% $2.33. T4 cheapest in 7/8 panels. Recall: -0.36pp, almost never used.
- Plan tool (Table 5): weak 30B SWE 13.6 -> 25.2; strong 550B 67.8 $3.31 -> 65.8 $2.33 (cost -30%,
  accuracy 0 to -2pp; it removes post-edit verification turns).
- Bash-only: 550B SWE 69.4 $1.11 vs full tools 65.8 $2.33; TB 50.6 vs 44.9. Mistral collapsed on
  SWE (45.4; 32.8% runs made no edit). Stuck detection: remind after 5 identical calls, stop at 8.

**2607.10569 Restricting to execute_code.** Claude Code (sonnet-4-6) and Codex CLI (gpt-5.5), 93
artifact tasks + 100 SWE-bench Mini, 3 seeds. No accuracy differences anywhere; code_only (one
persistent Python+bash REPL) -24.6% cost on artifact/Claude, -19.9% on SWE/Codex, +14.4% (n.s.) on
SWE/Claude. **Cross-seed unanimity: 90-95% on artifact tasks, 74-79% on SWE tasks.**

**2512.10398 Confucius Code Agent.** SWE-Bench-Pro (731, 3 seeds). Tool quality "advanced vs
simple" 51.0 vs 44.0 (largest effect). LLM-summary context management +6.6 on Claude 4 Sonnet,
+0.6 on 4.5 Sonnet. Cross-session notes 53.0 -> 54.4 (same tasks). Thinking budget 8k/16k/32k:
67.3/68.4/68.7. Sub-agents lost context and over-engineered.

## Verification and selection

**2501.14723 CodeMonkeys.** Sonnet 3.5, 10 candidates x up to 8 iterations, ~$4.58/problem.
Oracle 69.8%, random 45.8%, final 57.4% (half the gap). An untrained model judging patches alone
was *worse than test-count voting*; best: top-3 by votes, then the model writes a test to tell
them apart, runs it on candidates and the original, and decides (Fig. 6, numbers only in figure).

**2603.03800 Rubric-supervised critic (OpenHands).** Qwen3-4B trained on 24 o3-labelled failure
rubrics + sparse real outcomes. On 148 *mixed-outcome* SWE-bench problems: Best@2/4/8 66.7/72.6/
73.8 vs random 57.8; early stopping at 1.35 attempts. Critics without real-world data: 44-49,
**below random**. Full distribution Best@4 gains only +3.9 (Sonnet) / +2.6 (Opus).

**2602.03419 SWE-World.** Trained virtual test runner SWR; 55.0 -> 68.2 at K=8 (3 verdicts per
candidate, averaged). Verdict accuracy vs real Docker (Table 4): prompted Minimax-M2.1 0.740,
GLM-4.7 0.768 vs trained SWR-72B 0.770 - **strong prompted judges match trained ones, but are
lenient** (recall 0.84-0.89, precision 0.71-0.76). Reasoning before verdict 0.578 -> 0.712.

**2601.01426 SWE-Lego.** More turns in one attempt pays first and saturates ~100-140 turns; only
then do parallel rollouts win. At small K verifier types perform similarly; generative yes/no
beats regression heads as K grows (TTS@16: 49.6 vs 44.0 for OpenHands critic).

**2603.04304 V1.** Prompted *pairwise* comparison (rate both 1-10 side by side) beats pointwise
scoring: CodeContests 66.1 -> 73.3 (GPT-OSS-20B); SWE-bench Lite N=8: 33.3 pairwise vs 28.3
pointwise vs 26.3 none. Failure case: preferred a bigger two-file patch that regressed.

## Failures and reliability

**2607.09510 Failure as a Process.** 1,794 Terminal-Bench trajectories, 3 scaffolds x 7 models.
Decisive error at median step 7; lock-in ~step 12 (median fix window 1 step); first visible
symptom ~step 16. Root causes: **epistemic 57.9%** (false premise 30.7%, specification neglect
14.9%, output misreading 4.4%, ignored signal 4.1%, premature action 3.7%), competence 32.8%,
environment 9.4%. After lock-in: repair the wrong problem 24%, repeat 15%, checks that cannot
change the outcome 28%, fabricated success 15% (26% overall, 84% of it after lock-in).
Successful runs see error signals as often as failed ones (74 vs 72%) but act on them before
lock-in 92% vs 37%. A requirements-aware monitor caught more (recall 18.2 -> 28.8%).

**2604.17609 Agents Explore but Ignore.** Gold solution planted in the workdir: seen in ~80% of
Terminal-Bench runs, used in 37-50%; SWE-bench used 6-17%. Prompt ablation (Table 12, TB pass@1
on original tasks): base 40.0, +exploration 41.4, +curiosity 42.4, +reflection 42.9, **"investigate
every file you discovered; do not proceed until you have examined the available resources" 44.5**.
A reflection nudge at the moment of discovery: interaction 37.1 -> 53.3. Higher reasoning effort
raised use of discovered information; an edit tool lowered inspection.

**2601.06112 ReliabilityBench.** 20 synthetic tool tasks, k=2. pass@1 vs pass^2 gaps up to 12.5pp,
largest at choice points. Plain ReAct more robust than Reflexion (fault recovery 80.9 vs 67.3%).
The abstract's "pass@1 overestimates by 20-40%" is not derived from its data (weak paper).

**2604.17849 Reliability of Computer Use Agents.** OSWorld 361 tasks, n=3. GPT-5/S3 Pass@10 ~78%
vs Pass^10 ~36%. Temperature 0 / batch-invariant inference: mixed. **Ambiguity is a top variance
source:** clarified instructions GPT-5 Pass^3 .454 -> .576; a single clarified run beats blind
retries; failures are reasonable-but-wrong interpretations. Plans distilled from prior runs helped
GPT-5 and Kimi but hurt Claude.

## Terminal tasks and budgets

**2601.11868 Terminal-Bench 2.0.** 89 tasks (from 229), categories: software engineering, scientific
computing, security, debugging, sysadmin, games, personal assistant, model training, file ops,
ML, math, data processing, data science; tests check final container state. Top: Codex CLI +
GPT-5.2 62.9%. Most trials < 20 min and < 25 model calls. Failure classes: execution, coherence,
verification (incl. "claims tests passed but logs contradict", weak verification). Failed commands
9.2-26.7%; **largest command failure: executable not installed / not on PATH 24.1%**.
(Category counts and failure proportions are figures only.)

**2607.08964 Long-Horizon-Terminal-Bench.** 46 tasks, 90 min, best 28.3%. Unresolved runs:
**timeout 79%**, early self-exit 19%, harness 3%; timed-out runs were far from done (mean reward
0.10-0.35); ~90 near-misses vs ~45 passes; models quit at R 0.80-0.87 with 20 min left.

**2511.17006 Budget-Aware Tool-Use (BATS).** Budget Tracker appended after every tool response:
`<budget> Tool Budget Used: ##, Remaining: ## Make the best use of the available resources.</budget>`
with tiered guidance (HIGH >=70%, MEDIUM 30-70%, LOW 10-30% verify/finalize, CRITICAL <10% essentials
only). **SWE-bench Verified (Gemini-3-Flash, mini-swe-agent): budget 50 -> 36.8% vs 55.4% with the
tracker at equal cost (18.5 vs 18.9 cents)**; budget 70: 63.0 vs 70.0. Removing constraint-by-
constraint verification was the largest BATS ablation drop (18.7 -> 15.4).

**2602.11541 INTENT (budget-constrained agents).** Prompt-only budget info still overspent in
12-33% of tasks; a hard pre-call cost check with pessimistic success estimates won (pass 63.8-76.0
vs 30.9-48.5 prompt-only).
