# Develop

| Path | What |
|---|---|
| [incentive/](incentive/README.md) | SN62 reward calculator, verified against live platform weights |
| [agent/](agent/README.md) | Contract-compliant single-file agent scaffold with offline tests |

```bash
uv venv .venv && VIRTUAL_ENV=.venv uv pip install pytest requests
.venv/bin/python -m pytest -q develop
```
