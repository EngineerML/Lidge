# Problem-solving agent (SN30)

`agent.py` is our own single-file agent for the Ridges Problem Solving competition. It follows the
agent contract (`agent_main({"problem_statement": ...}) -> str` diff), uses only the standard
library and `requests`, and sends inference through `SANDBOX_PROXY_URL` with
`Authorization: Bearer $OPENROUTER_API_KEY`.

The design comes from `research/notes/2026-11-01_agent_improvements.md` (16 papers read in full);
kaito was used as a reference for ideas, not as source.

| Part | What it does | Evidence |
|---|---|---|
| Opening | Environment survey (tools present, versions, packages, tree), and a check of every path and file name the task mentions (exists / not found) | Missing executables are the top command failure; false premises are 31% of failures |
| Checklist gate | `record_checklist` (deliverables, requirements, assumptions, interpretation) is required before any file in the working directory can change; re-shown every 8 steps | Specification neglect, ambiguity as a main variance source |
| Prompt | "Investigate every relevant file you discover; do not proceed until you have examined the available resources"; reproduce worked examples; first complete version early | Best-measured curiosity prompt (+4.5 pass@1) |
| Meter | `[time left | budget left | tier]` after every tool result, tier guidance (medium/low/critical), hard pre-call guard with a 15% reserve for verification, proxy 429 handled as budget exhausted | Budget Tracker +18.6pp at equal cost; prompts alone overspend |
| Milestone | At half of time or budget with no change, demands a first version at the exact path | Timeouts are 79% of long-horizon failures |
| Finish gate | First `finish` returns the task, checklist and changed files and asks for fresh checks; the next `finish` is accepted only after a command ran | Fabricated success clusters late; verification is the largest BATS ablation |
| Tool guards | exit code, runtime, `(no output)`, final cwd if it changed; slow commands become background jobs; repeated identical calls warned at 5, refused at 8; nudge after 5 failing commands | Stuck detection, early epistemic errors |
| Second attempt | Only if attempt A is not verified, budget/time left >= 40% and the proxy budget is not exhausted: restore the baseline (including pre-existing git-ignored files), run attempt B with A's notes as unverified hints, then select: verified beats unverified, otherwise one pairwise judgment in both orders, A unless both orders pick B | Extend one attempt first; pairwise beats pointwise; small-K gains are small |
| Context | Elides old tool output over 1,200 chars once prompts pass 60k tokens; harder on a context-length error | Rule-based elision cheapest |
| Patch | Diff against a private git baseline: works in non-repo folders, never touches the repo's `.git`, keeps files the agent wrote even if git-ignored, drops symlinks, nested repos, bytecode and new files over 10 MB; checks the patch applies to the baseline | Symlinks/submodules score 0 |

Defaults (`MODELS`, `REASONING_EFFORT`) can be overridden locally with `RIDGES_AGENT_MODELS` and
`RIDGES_AGENT_EFFORT`; the model choice still has to be measured.

## Test

```bash
uv venv .venv && VIRTUAL_ENV=.venv uv pip install pytest requests   # once
.venv/bin/python -m pytest -q develop/agent/tests                    # offline, fake proxy, no spend
```

The tests cover the checklist gate, the finish gate, the budget 429 path, the second attempt with
restore and selection, the pairwise judge, repeated-call refusal, excluded symlinks / bytecode /
nested repos, and that the patch applies to a clean copy.

## Not done yet

- No run against real tasks or a real model: needs an OpenRouter key and the local evaluation loop
  (N tasks x 3 runs, all-3-pass, cost per task).
- Model and reasoning effort not chosen by measurement.
- Optional persistent Python tool (cost saver on data tasks) not added.
