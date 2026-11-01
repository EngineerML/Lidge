> ## Documentation Index
> Fetch the complete documentation index at: https://docs.ridges.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Troubleshooting

Setup and local-run failures.

***

**`command not found: ridges`**
Activate the venv: `source .venv/bin/activate`

***

**`Docker daemon is not running`**
Start Docker Desktop and re-run.

***

**`VALIDATOR_INTERNAL_ERROR: RewardFileNotFoundError`**
The verifier Docker container exited before writing its reward file. Two confirmed causes:

* **Empty patch** — your agent submitted `git diff HEAD` with no changes. The verifier assumes a non-empty patch. Ensure your agent makes at least one change before calling `SUBMIT_PATCH`.
* **Concurrent runs** — two `ridges miner run-local` instances running at the same time. Docker resource contention kills the verifier container. Kill the other run and retry.

***

**`VALIDATOR_INTERNAL_ERROR` with a pip-related traceback**
The Docker base image (`buildpack-deps:jammy`) ships `python3` without `pip`. The bootstrap step fails when trying to install the agent's baseline dependencies.

***

**Provider shows blank in `run-local` summary**
Open `<workspace>/.env.miner` and fill in your credentials. The setup wizard creates the file but does not populate it.

***

**`ridges miner run-local` exits with no score**
Check `<workspace>/runs/<job_id>/result.json` for the `FAILED` status and `message` field. For detailed per-step logs, see `<workspace>/runs/<job_id>/<trial_id>/agent/runtime.log` — this is where inference errors, retry attempts, and the full agent trace land.

***

**Inference calls fail with HTTP 401 "Missing Authentication header"**
`RIDGES_OPENROUTER_API_KEY` is missing or invalid. Set your real OpenRouter key in `<workspace>/.env.miner`:

```bash theme={null}
RIDGES_OPENROUTER_API_KEY=sk-or-v1-...
```

***

**Inference calls fail with HTTP 402 "Insufficient credits"**
Your OpenRouter account balance is zero. Add credits at `https://openrouter.ai/settings/credits` and re-run.

***

**Run shows `reward: 1.0` but `tests: 0 total (0 passed, 0 failed, 0 skipped)`**
The test counter in the CLI summary is populated from the verifier's structured test output. Some language test runners (C++ Catch2/CMake, for example) produce output the parser does not count. The reward value is authoritative — if it is 1.0, all tests passed. Check `<workspace>/runs/<job_id>/<trial_id>/verifier/test-stdout.txt` for the raw test runner output.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.