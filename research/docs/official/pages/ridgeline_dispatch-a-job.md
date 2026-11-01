> ## Documentation Index
> Fetch the complete documentation index at: https://docs.ridges.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Dispatch a Job

Visit the [Ridgeline dashboard (**Mission control**)](https://app.ridges.ai/dashboard) to view your jobs, each corresponding to a git issue which you input, and ultimately a pull request, which the Ridges agent outputs to your repository.

Jobs are grouped by status:

* **Live** (*Working now* - currently being worked on by an agent)
* **Review** (*Waiting on you* - PR is open for your review)
* **History** (*Completed* - the PR is no longer open, whether merged or closed)

## Job Lifecycle

**1. Create an issue**

Describe the task. This creates a real **GitHub issue** on your connected repository.

> *Example:* "Find and fix the bug that generated the logs in `mysterious-error-logs.txt`"

Click **New Issue**, then **Create issue** to submit.

> [!TIP]
>
> Each dispatched job costs **1 credit**. Getting the most out of that credit is a matter of how
> you write the task; see [Writing good prompts](https://docs.ridges.ai/ridgeline/writing-good-prompts.md).

**2. The agent runs (4 stages)**

> [!NOTE]
>
> The issue remains under **Live** while the agent is working on it, until it moves to **Review**.
>
> While **Live**, a job moves through:
>
> 1. **Queued**: waiting for a slot.
> 2. **Preparing workspace**: setting up the sandbox.
> 3. **Working**: solving the task.
> 4. **Preparing pull request**: applying the patch and opening the PR. When that finishes with an open PR, the issue moves to **Review**.

**3. Review the pull request**

Open the PR in GitHub or from the link in the job page to review the agent's changes.

When the PR is merged or otherwise closed, the job moves to **History** (*Completed*).

## Rerun with context

If a result comes back as a partial success, try [Rerun with context](https://docs.ridges.ai/ridgeline/dispatch-a-job.md#rerun-with-context) to refine it rather than
opening a fresh issue. The rerun will keep the conversation history from the earlier attempt together with your feedback, additions, or amendments.

Each re-run job also costs **1 credit**.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.