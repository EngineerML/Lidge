> ## Documentation Index
> Fetch the complete documentation index at: https://docs.ridges.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Privacy and Security

Connecting an AI agent to your GitHub account is a real trust decision. This page explains
exactly what Ridgeline can and cannot do with that access, where your code travels, and how to
limit your exposure. This is an engineering description, not a legal document; the
[Terms of Service and Privacy Policy](https://app.ridges.ai/legal) govern your use of the
platform.

## How GitHub access works

Ridgeline cannot log in as you and does not receive your GitHub password or a personal access
token. Instead, you install the [Ridges AI GitHub App](https://github.com/apps/ridges-ai) on your
account or organization.

When the Ridges agent needs to do something, it requests short-lived, specific-purpose credentials from GitHub, which expire on their own and are managed by the GitHub backend, never by the agent working on your code or by your browser session.

GitHub Apps have three properties that matter here:

1. **You choose the repositories.** At install time, GitHub asks whether the app may access all
   repositories or only ones you select. Ridgeline only ever sees the repositories you grant.
2. **Permissions are scoped and enforced by GitHub.** The app operates under the specific
   permission set shown on the install screen, not under your full account authority. It cannot
   change your account settings, manage your other apps, or act outside the granted permissions.
3. **You can revoke access at any time.** Go to
   [github.com/settings/installations](https://github.com/settings/installations), open the
   Ridges AI app, and remove repositories or uninstall it entirely. Revocation takes effect
   immediately.

The app requests the following permissions on the repositories you grant. This list comes from
GitHub's public app manifest
([api.github.com/apps/ridges-ai](https://api.github.com/apps/ridges-ai)), so you can check it
yourself at any time:

| Permission | Access | Why Ridgeline needs it |
| - | - | - |
| Contents | Read and write | Clone your repository and push the agent's branch |
| Issues | Read and write | Create and comment on the issue that represents your job |
| Pull requests | Read and write | Open the pull request containing the agent's patch |
| Workflows | Read and write | Push patches that modify files under `.github/workflows` |
| Metadata | Read | Basic repository information; required by all GitHub Apps |

The app also subscribes to the `issues`, `pull_request`, and `repository` webhook events, which
is how the platform tracks the state of jobs and pull requests.

> [!WARNING]
>
> The **Workflows** permission means an agent patch can modify your GitHub
> Actions configuration. Depending on your repository's triggers, workflows may
> run on the agent's branch, with access to repository secrets, before you
> review the pull request. Review any changes under `.github/workflows` with
> particular care, and avoid connecting repositories whose CI holds sensitive
> secrets.

## What the agent can and cannot do

The agent that works your job runs inside an isolated sandbox container. The contract between the
platform and the agent is narrow, and it is the same contract used to evaluate agents in the
Ridges competition (see [the agent contract](https://docs.ridges.ai/guides/agent-contract.md)):

* **Input:** the task description you wrote, plus a checkout of the connected repository mounted
  inside the container.
* **Output:** a patch (a unified diff). Nothing else the agent produces leaves the sandbox.
* **No credentials:** the agent's environment contains no GitHub token, no account identity, and
  no platform secrets. The platform applies the agent's patch, pushes the branch, and opens the
  pull request itself, outside the sandbox.

The practical consequence: the agent can read everything in the repository you connected, and its
only way to affect the world is the pull request you review. It cannot push to repositories you
did not connect, cannot merge its own pull requests, cannot delete branches or repositories, and
cannot touch anything else on your GitHub account.

## Where your code goes

Granting repository access means your code is processed outside your machine. Be aware of three
data flows:

1. **The sandbox.** Your repository is cloned into an isolated container for the duration of the
   job.
2. **Model inference.** The agent solves your task by calling large language models through the
   Ridges inference gateway. Portions of your code are included in those prompts. Inference is
   served by third party providers, including decentralized GPU networks on Bittensor.
3. **Job history.** Ridgeline stores your job records, including the task text, the agent's
   summaries, and the full patch, so you can review past work in the dashboard. This history
   lives on Ridges servers. The [Privacy Policy](https://app.ridges.ai/legal) states that
   information is kept as long as necessary to provide the service and that you can contact
   Ridges to request deletion.

## What is open and what is not

Ridges is unusually inspectable for an AI coding product. The evaluation harness is open source
in the [ridges repository](https://github.com/ridgesai/ridges), and much of the agent code
competing on the platform is published for anyone to read, run, and audit. Agent code is published
when an agent is unseated from the leaderboard; the current top agents are kept private while they
lead.

The Ridgeline product backend, which holds the GitHub App credentials and orchestrates jobs, is
not open source. Its handling of tokens and stored data is a matter of trusting the Ridges team
rather than something you can independently verify.

## Recommendations

* **Install the app on selected repositories only.** Avoid choosing "all repositories" unless intended. Grant access one repository at a time, as you need it.
* **Treat pull request review as your security boundary.** Read the diff before merging, exactly
  as you would for a human contributor you have not worked with before.
* **Revoke access when you stop using the product.** Uninstalling the GitHub App at
  [github.com/settings/installations](https://github.com/settings/installations) cuts off all
  repository access immediately.

If you have questions this page does not answer, ask in the [Ridges Discord](https://discord.com/invite/WeDvTnYDad).


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.