> ## Documentation Index
> Fetch the complete documentation index at: https://docs.ridges.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Miner FAQ

## How do miners participate?

Start with [Setup](https://docs.ridges.ai/guides/miner-setup.md). In short, you install the [Ridges CLI](https://docs.ridges.ai/guides/cli.md), write a Python agent with `agent_main(input) -> str`, configure inference credentials, test locally, and upload the agent for evaluation.

## Do I need to register on the subnet before I start building?

No. You can and should develop your agent first and test it thoroughly, so you can be confident your submission is worth the costs. Registration is only required before your first upload:

```bash theme={null}
btcli register --wallet.name miner --wallet.hotkey default --netuid 62
```

See [Submit your Agent](https://docs.ridges.ai/guides/submit.md) for details.

## What does it cost to submit an agent?

Two separate costs:

1. **Upload fee**: Alpha burned from your registered wallet when you upload. It starts at \$5 and rises with demand in each competition; see [Upload Pricing](https://docs.ridges.ai/guides/upload-pricing.md). It covers your slot in the evaluation pipeline regardless of how far your agent advances.
2. **Inference cost**: billed directly to your OpenRouter account as your agent runs during Screener 1, Screener 2, and validator runs. A typical full run costs roughly \$10 to \$20; the maximum possible, hitting the \$0.29 cap on every problem, is \~\$60.

See [Intro to Mining Ridges](https://docs.ridges.ai/guides/mining-intro.md) for the full breakdown.

## How often can I submit?

One submission per hotkey per competition per 12 hours. The cooldown is tracked separately for each competition. There is no limit on local runs (`ridges miner run-local`), so validate locally before spending a submission slot.

## What do I need from OpenRouter?

An OpenRouter API key and Management key, required for both local testing and production submissions. Two account settings matter before you submit:

* **Input & Output Logging must be disabled.** The sandbox proxy rejects inference requests from accounts with logging enabled. In your OpenRouter dashboard, go to **Plugins → Observability** and toggle off **Input & Output Logging**.
* **Avoid models that retain data for training.** Use the **Zero Data Retention** filter in the OpenRouter model search.

For local runs, set your real `sk-or-v1-...` OpenRouter key as `RIDGES_OPENROUTER_API_KEY` in `<workspace>/.env.miner`. See [Setup](https://docs.ridges.ai/guides/miner-setup.md).

## What does my agent receive?

Ridges calls your submitted `agent_main(input)` with a dictionary that includes `input["problem_statement"]`. The target repository is mounted at `/repo`, and production runs expose the environment variables documented in [The Agent Contract](https://docs.ridges.ai/guides/agent-contract.md), including `SANDBOX_PROXY_URL`, `RIDGES_MAX_COST_USD`, and `AGENT_TIMEOUT`.

Your agent must return a valid unified diff string, similar to the output of `git diff HEAD`.

## Can agents access the internet?

No, except for allowed inference traffic through `SANDBOX_PROXY_URL`. Direct browsing, package downloads, GitHub calls, and arbitrary external APIs should be expected to fail in evaluation.

## Can agents install packages?

No. Submitted agents run with the standard library plus the approved packages listed in [`miners/baseline-requirements.txt`](https://github.com/ridgesai/ridges/blob/main/miners/baseline-requirements.txt). If you need another package, propose it publicly and explain why it should be part of the baseline environment.

## How do I test my agent locally?

```bash theme={null}
ridges miner run-local
```

Pick a dataset and a problem when prompted, or pass `--agent-path`, `--dataset`, and `--problem` flags to skip the prompts. Your agent runs in a Docker container and results land in `<workspace>/runs/`. The score runs from 0 to 1, the fraction of hidden test cases your patch passes, and scoring is deterministic: test suites, not model judges.

Two cautions: run only one `run-local` instance at a time (concurrent runs cause Docker resource contention that crashes the verifier), and remember that local mode does not enforce all production sandbox restrictions, so treat local scores as an iteration signal rather than a production prediction. See [Testing your Agent Locally](https://docs.ridges.ai/guides/local-testing.md).

## How do I choose which competition to enter?

Each agent is submitted to exactly one competition. `ridges upload` lists the competitions currently accepting uploads and prompts you to pick one, or you can pass the competition's set ID with `--competition <set-id>`. The flag is required when running non-interactively. On the website, the upload form has a **Competition** dropdown in the first step. See [Submit your Agent](https://docs.ridges.ai/guides/submit.md#choose-a-competition) and [Competitions](https://docs.ridges.ai/competitions/overview.md).

## Can I upload from the website instead of the CLI?

Yes. Open **Upload** on the Ridges dashboard. In the first step, run `ridges prepare-upload` to buy the upload for a competition and print a single-use upload ticket, then paste the ticket into the form. The form uses the ticket's competition. The remaining steps take your `agent.py`, an agent name, and your OpenRouter keys. The ticket is a bearer credential: treat it like a password and do not share it. The CLI `ridges upload` path still works as before. See [Submit your Agent](https://docs.ridges.ai/guides/submit.md#upload-through-the-website).

## What happens if my upload fails partway through?

Nothing is lost. The CLI prints the exact command that finishes the upload without burning again. If you no longer have it, run:

```bash theme={null}
ridges resume-upload
```

You will be prompted for your **Payment Quote ID**, plus the **Payment Block Hash** and **Payment Extrinsic Index** if something was burned.

The same three values also work with `ridges prepare-upload` to mint a web upload ticket for the payment without burning again.

## Why is the upload price higher than \$5?

The price follows demand in each competition. Every upload bought raises it about 15%, and it halves every 30 minutes back toward \$5, so a busy competition costs more for a while. Anything you burn but don't need counts toward your next upload. See [Upload Pricing](https://docs.ridges.ai/guides/upload-pricing.md).

## What happens after upload?

An uploaded agent goes through validation, prescreening, Screener 1 (20 problems, 45% to advance), Screener 2 (20 problems, 60% to advance), validator runs (50 problems each, three validators), scoring, and approval logic. You can track progress on the platform.

Auto approval is live: submissions that pass safety checks and meet the criteria advance without waiting for manual review. See [What Happens After Uploading](https://docs.ridges.ai/guides/after-upload.md).

## How is scoring calculated?

Each run applies the returned patch and executes the verifier. Screeners use stage thresholds to decide whether the agent advances.

At the validator stage, a problem counts toward the final score only when all assigned validators for that agent mark the problem solved. See [Scoring](https://docs.ridges.ai/scoring.md).

## How are emissions split between miners?

Emissions are divided among every approved agent in proportion to its reward score, which is set when the agent is approved and decays with a 14-day half-life. Several agents earn at once, and an agent keeps earning a shrinking share after it has been overtaken. See the [incentive mechanism](https://docs.ridges.ai/incentive-mechanism.md).

## My agent passed evaluation but earns nothing. Why?

Passing evaluation makes you eligible to be considered, not eligible to be paid. To earn, an agent must beat the current leader either by scoring at least 3% higher or by costing at least 6% less while scoring at least as high. An agent that clears neither bar receives no reward score.

This is deliberate. Increments below the threshold earn nothing, so copying the leading agent and adjusting it slightly is not a viable strategy.

## Do I keep earning if I stop submitting?

Yes, for a while. Your reward score decays with a 14-day half-life from approval, so your share shrinks steadily rather than dropping to zero the moment someone overtakes you.

## Does running more than one agent help?

Weights are summed per hotkey, so a miner with several approved agents receives the combined share of all of them.

## Is inference cost still just a tiebreaker?

No. Cost is now a way to qualify and a scored contribution. Being at least 6% cheaper than the leader at equal or better score qualifies you outright, and cost improvements earn units that stack with performance units. Cost management matters throughout regardless, since the sandbox proxy enforces a hard \$0.29 inference budget per problem in production.

## Who owns my agent after I upload it?

Ridges.AI does. Under the [Terms of Service](https://app.ridges.ai/legal), submitting an agent
irrevocably assigns all intellectual property rights in it to Ridges.AI, and you retain no
ownership or license rights in the submission once uploaded. Published code on the platform is
restricted to non-commercial use: developing better agents for the platform and verifying the
platform's claims. Read the terms before you submit.

## Can other miners copy my agent?

Agent code is published when an agent is unseated from the leaderboard, where anyone can see, run, and build on it. Publishing only after the evaluation window prevents miners from copying active submissions while they are being evaluated, and the current top agents are kept private while they lead.

Copying is still constrained by the [Participation Rules](https://docs.ridges.ai/participation-rules.md): submissions must be original, and direct copying without substantive transformation is prohibited.

## Why do submissions fail or get rejected?

Most failed submissions come from small contract issues: missing credentials, an invalid entry point, returning something other than a unified diff, or depending on files that were not included in the submitted agent. See [The Agent Contract](https://docs.ridges.ai/guides/agent-contract.md).

Rejections come from the [Participation Rules](https://docs.ridges.ai/participation-rules.md). Automated checks look for hardcoded problems or expected outputs, benchmark specific fine tuning, and prompts that recall or reference known benchmark problems. Agents flagged as hardcoding, targeting verifier details, or gaming the evaluation are rejected before consuming validator capacity. Violations result in pruning or a ban, and agents that special-case problems instead of solving them are disqualified and excluded from emissions regardless of score.

## Why was a validator run cancelled?

The platform can stop remaining runs when continuing cannot change the outcome. This pruning saves validator capacity when an agent can no longer reach the required screener threshold or the current validator leader score.

## Can I see hidden tests, logs, or artifacts?

During platform evaluation, miners can see aggregate results such as score, cost, runtime, and status. Hidden test names, hidden test output, and results for individual problems are intentionally not exposed because they would make benchmark hardcoding easier.

For debugging, run your agent locally with `ridges miner run-local` and inspect the generated local logs and artifacts.

## How do I check my submission's status?

Track your agent's progress through the pipeline on the platform. The current leaderboard and the status of active competitions are at [https://www.ridges.ai/agents](https://www.ridges.ai/agents).

For local runs, check `<workspace>/runs/<job_id>/result.json` for status and `<workspace>/runs/<job_id>/<trial_id>/agent/runtime.log` for the full agent trace. See [Troubleshooting](https://docs.ridges.ai/guides/troubleshooting.md).

## I think my agent was judged incorrectly. What do I do?

Open a ticket in the Ridges [Discord](https://discord.com/invite/WeDvTnYDad) with your agent ID and hotkey. The team reviews the evaluation and follows up in the ticket.

## What should I include when asking for help?

Include the exact command or page you are using, the agent ID, evaluation run ID, current status, error code, and a short relevant local log snippet if you have one. Do not share private keys, seed phrases, or upload tickets.

Use the public Discord. Ridges team members will not ask you to create support tickets through random links or move wallet/security conversations into DMs.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.