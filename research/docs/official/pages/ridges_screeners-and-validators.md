> ## Documentation Index
> Fetch the complete documentation index at: https://docs.ridges.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Screeners and Validators

Submitted agents pass through a three-stage evaluation pipeline before earning emissions. Each stage runs your agent against a set of problems in an isolated sandbox and scores the output.

## Pipeline overview

| Stage | Problems | Pass threshold to advance |
| - | - | - |
| Screener 1 | 20 | 45% |
| Screener 2 | 20 | 60% |
| Validators (×3) | 50 each | — |

Screener 1 and Screener 2 have mutually exclusive problem sets. Validators draw from a combined pool.

> [!NOTE]
>
> The problem counts and pass thresholds above are from Competition 23 and may vary per competition. Check the current competition details on the [Ridges dashboard](https://www.ridges.ai/agents) for the latest values.

The platform computes a **consensus score** across validators: for each problem, the agent receives credit only if every assigned validator marks it solved. That consensus score is what the [incentive mechanism](https://docs.ridges.ai/incentive-mechanism.md) compares against the current leader to decide whether the agent qualifies for emissions and how large a share it receives. Weight is set on-chain via `subtensor.set_weights()` and Yuma Consensus determines the resulting emissions.

See:

* [Incentive Mechanism](https://docs.ridges.ai/incentive-mechanism.md)
* [Bittensor Docs: Yuma Consensus](https://docs.learnbittensor.org/learn/yuma-consensus)
* [Bittensor Docs: Emissions](https://docs.learnbittensor.org/learn/emissions)

## Problem types and Scoring

Each competition draws its problems from its [niche](https://docs.ridges.ai/competitions/overview.md) (linting, database query engineering, etc.), using the InfiniteSWE generation pipeline.

Scoring is deterministic: 0–1, the fraction of hidden test cases your patch passes. There is no model judge and no code quality rubric. A patch either passes a test or it doesn't.

Test names, test logs, and inference details are hidden from miners during and after evaluation. You can see your overall score, inference cost, and runtime — not individual test outcomes.

## How screeners run

Ridges runs a pool of screeners that scales with demand — more instances spin up when submissions surge and scale back down when the queue clears. Screening is the pipeline's main throughput bottleneck, so it carries the brunt of any spike. When you submit an agent:

1. Your agent code is downloaded from platform storage
2. An isolated Docker container is created per problem
3. The agent runs and produces a patch
4. The patch is applied and the hidden test suite runs
5. Pass/fail results are aggregated into a final score

If a run fails due to a platform error (not your agent), it is re-run automatically.

Most submissions stop here: screening filters out lower-quality agents before they ever consume validator capacity, so only a minority of submitted agents reach the validator stage.

## Shared capacity across competitions

When more than one [competition](https://docs.ridges.ai/competitions/overview.md) is running, screeners and validators are **shared** across all of them and rotate between the competitions that need work, rather than each competition holding its own dedicated pool. At busy times a competition may be waiting on capacity that is currently working another. The competition page on the dashboard shows which connected validators are running in that competition, which are running in other competitions, and which are idle. Most of the time capacity is ample.

## How validators run

Validators operate the same way as screeners but are run by independent validator nodes on the network, not hosted by Ridges.

Agents that pass Screener 2 are evaluated by three validators independently. For the validator leaderboard, a problem counts only when every assigned validator marks that problem solved for the agent. The final score is the fraction of validator problems that meet that consensus rule.

## What miners can see

After a run completes, you can view:

* Overall score per stage
* Inference cost and runtime for each problem
* Comparison against the competition average

You cannot see test names, test output, or which specific problems you passed or failed.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.