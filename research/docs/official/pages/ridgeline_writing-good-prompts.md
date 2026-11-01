> ## Documentation Index
> Fetch the complete documentation index at: https://docs.ridges.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Writing Good Prompts

Ridgeline is an end-to-end coding agent, and does not need to be managed interactively. It costs one credit per job.  Write detailed acceptance criteria for the end result you want, rather than attempting to managing the agent through a process step-by-step, as you might with another code assistant.

> [!NOTE]
>
> The agent is set up to work in **Python**: its sandbox comes with Python and a broad library set, so it installs your dependencies and runs your test suite. It is directed to stick to Python — for other stacks (Node, Go, Rust, and the like) it will not install a toolchain or run your suite, and instead verifies with lighter checks such as confirming the code compiles. So while it can read, reason about, and edit any codebase, don't count on it running a non-Python suite today. The advice below matters most, and pays off most, for a repo it can run.

Ridgeline is built for making changes to a codebase. It will pull a reference or install a lightweight package when a coding job calls for it, but it is not a research or data-gathering tool — broad, open-ended jobs that aren't really about code tend to spend a job's budget without landing a clean result. Scope your prompt to the coding change you want.

Your prompt is the whole brief. The agent's first move is to expand what you wrote into a working spec — reading your repository's structure to ground it — and then it runs unattended, with no way to come back and ask a follow-up. So describe the outcome you want clearly and completely, and let it work out the *how*. Because the whole job hinges on that written brief, it is worth drafting and sharpening it wherever you write most clearly, then dispatching the polished version.

## Practice Test-Driven Development

A Ridgeline agent does not just read your repository; it runs inside a container with your code mounted, and it can compile files, run scripts, and execute test, then read the results and act on them. It works on a feedback loop, rather than emitting a single guess, provided you have set up your repo to be easy to work with.

Give Ridgeline a definition of success that it can verify. State the end result as acceptance criteria that can be encapsulated as tests.

Two patterns work well:

* Write the tests yourself and ask for the code that makes them pass.
* Describe the features in detail, ask for a test suite that covers the specification, then ask for the implementation that satisfies it.

## Provide context and constraints

* **Documentation**: If your project has a test command, name it. If it needs setup, say so. This lets the agent close the loop efficiently instead of guessing at your conventions.
* **Point to the relevant files or modules** if you know where the work belongs. It saves the agent from searching and keeps the change scoped.
* **State the constraints** that matter: public APIs that must not change, libraries to prefer or avoid, performance or style requirements.
* **Say whether it is a fix or a feature.** A fix should be a minimal, backward-compatible change to existing behavior; the agent will keep it targeted and avoid new files. A feature is built end-to-end, so give it acceptance criteria and expect the agent to build the behavior first and its tests second.
* **Scope the job.** One well-defined change per job produces a cleaner result than a broad, open-ended ask. Split large efforts into separate jobs.
* **Artifacts**: When squashing a bug or doing root cause analysis, give the agent everything it needs to reproduce the failure, if possible, and any error messages, logs, or detailed descriptions of the events around the failure. A bug the agent can reproduce is a bug it can confirm it has fixed.

## Take advantage of the agent's code execution capabilities

Ridgeline does not just write a change and hand it to you unverified. The agent runs inside a container
with your repository mounted, and it can **execute your code**: install dependencies, run scripts, and
invoke your test suite. Before it delivers a PR, it can confirm that its change actually does what you
asked, on your code, in your environment.

There is a catch, and it is the whole point of this page. **The agent can only validate what your repo
lets it run.** If your tests pass from a clean checkout, the agent can prove its fix works. If your tests
need an undocumented environment variable, a database nobody mentions, or a manual setup step buried in
someone's head, the agent hits the same wall a new hire would, and it falls back to weaker signals like
"the code compiles."

A repo that is easy for a new engineer to run is a repo the agent can validate. The setup below is worth
doing once, and it pays off on every job.

## Give it a test command that works from a clean checkout

The single highest-leverage thing you can do is make your tests runnable in one documented command from a
fresh clone. That is what turns "the agent thinks this is right" into "the agent ran your suite and it
passed."

* Document the command plainly: `pytest` (or `python manage.py test`). A non-Python command like
  `npm test` or `go test ./...` documents intent, but the agent sticks to Python and won't run it
  today — see the note at the top of this page.
* Make sure it passes on `main` before you dispatch a job. Ridgeline runs your suite to record a baseline
  *before* it changes anything, and treats every failure already present as out of scope — so a bug
  hiding behind a test that is red on `main` will be read as pre-existing and left alone, unless that
  failure is the exact behavior your task describes.
* If setup is needed first, script it: `make setup && make test`, not a paragraph of prose.

## Make dependencies installable without a human

The agent installs your dependencies itself before it starts, running a standard install
(`pip install -r requirements.txt`, `pip install -e ".[test]"`). Keep that install boring so it succeeds on
its own: standard, lightweight, pip-installable Python packages. Heavy or unusual toolchains may not
install, and it cannot reach your **private** services or secrets or ask you for a credential mid-run —
its environment has to be reconstructable from what is in the repo.

* Declare dev/test dependencies (e.g. a `[test]` extra) so the suite's requirements come with them, and
  install with a standard command the agent can find and run.
* Pin dependencies in a lockfile (`requirements.txt`, `pyproject.toml`) for a reproducible install.
* Keep dependencies lightweight and standard — the agent is built to fetch ordinary Python packages, not
  to stand up heavy or exotic toolchains.
* Avoid tests that reach out to your private or live third-party services. Stub or mock them.

## Remove hidden setup

Anything the agent needs but cannot discover from the repo is a step it will skip.

* Provide example config: commit a `.env.example`, and default sensibly when a value is missing.
* If a test needs a service like a database, start it as part of the test command (for example a
  `make test-integration` target that spins one up), rather than assuming it is already running.
* Ship seed data and fixtures the tests depend on.

## Keep the feedback loop fast

Every job has a time budget. A suite that takes forty minutes leaves the agent no room to run it, read the
result, and iterate. It will run a smaller slice or skip verification entirely.

* Keep the core suite fast, or expose a quick subset the agent can target.
* Make failures readable. Clear assertion messages tell the agent exactly what broke.

## Expose the other checks you rely on

If your definition of "good" includes more than tests, make those runnable too, so the agent can hold
itself to the same bar you would.

* A lint command: `ruff check`, `eslint`, `golangci-lint`.
* A type check: `mypy`, `tsc --noEmit`.
* A build step, if a passing build is part of done.

## Ask for validation in your prompt

Once the repo supports it, tell the agent to use it. Name the command and state the bar.

* "Run `npm test` and make sure the full suite passes before finishing."
* "Add a test that reproduces the reported bug, confirm it fails, then fix it and confirm it passes."


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.