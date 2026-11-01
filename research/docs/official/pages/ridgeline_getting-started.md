> ## Documentation Index
> Fetch the complete documentation index at: https://docs.ridges.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Building Software with Ridgeline

Ridgeline lets you solve problems with our state-of-the-art coding agent derived from the Ridges competitions.

Ridgeline is designed as an end-to-end software engineering agent, rather than as an interactive assistant. Provide a complete specification of the desired result, and the agent computes the code solution from a securely isolated compute environment, and opens a pull request on your GitHub repo just like a human developer would.

One pull request costs one credit.

## The Ridgeline Agent Pipeline:

The agent works unattended, in a sandbox managed by Ridges.AI.

The Ridgeline agent delivers a pull request to your repo, which can only be merged with your approval.

The full flow depends on two inputs you provide: the issue brief you write, and your repository itself, i.e. whether it can be installed and tested from a clean checkout.

See [Ridgeline: Writing Good Prompts](https://docs.ridges.ai/ridgeline/writing-good-prompts.md).

The agent executes the following lifecycle for each job/issue you submit:

1. **Sets up the environment** from what is in the repository, installing dependencies with a standard command.
2. **Runs your test suite before changing anything**, to record a baseline. Failures already present are treated as out of scope, unless the failure is the exact behavior your task describes.
3. **Reads your brief and turns it into a spec.** The issue text is the whole task description. The agent expands it into a working specification grounded in your repository's structure, then plans the change from that. It cannot come back to ask a follow up question, so what you wrote is all it has.
4. **Makes the change.**
5. **Runs your code again to check its own work**, at the cheapest level that gives real confidence: the narrowest test that covers the change first, the broader suite at most once at the end. The bar is simple: nothing that passed before the change may fail after it.
6. **Reviews its own diff** against your brief and that spec. A separate review pass flags unrelated file changes, leftover debug output, scaffolding, and broken references. Cleanup issues are fixed, and a patch that misses part of the task is sent back for another attempt, before anything reaches you.
7. **Opens a pull request** for you to review.

## Usage Overview

**1. Connect GitHub**

Sign in and connect a repository. Start with a low stakes repo until you know what to expect.
See [Connect GitHub](https://docs.ridges.ai/ridgeline/connect-github.md).

> [!TIP]
>
> Read [Privacy and Security](https://docs.ridges.ai/ridgeline/privacy-and-security.md) for what Ridgeline can and
> cannot do with your GitHub access.

**2. Get credits**

Either subscribe with cash (fiat) payments, or earn credits by locking stake on the Ridges Bittensor subnet.
See [Get credits](https://docs.ridges.ai/ridgeline/credits.md).

**3. Dispatch a job**

One job costs one credit.
Open an issue describing the work. The agent runs it and opens a PR.
See [Dispatch a job](https://docs.ridges.ai/ridgeline/dispatch-a-job.md).
\[!TIP] One clear and complete task description beats many small ones. See [Writing good prompts](https://docs.ridges.ai/ridgeline/writing-good-prompts.md).


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.