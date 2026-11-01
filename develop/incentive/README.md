# Incentive model

`ridges_incentive.py` reimplements the SN62 reward math (`repos/ridges/utils/incentives.py`,
`api/incentives.py`): qualification (3% score or 6% cost at equal score), log-compounded
improvement units, the `1 + sqrt(h/6)` time multiplier, benchmark-phase points, 14-day decay and
the per-competition / per-hotkey weight split.

`tests/test_against_live.py` checks it against the 2026-11-01 snapshot: every stored reward score,
every unit count from its deltas, the benchmark winner's points, and all 35 hotkey weights from
`/scoring/weights` (within 1e-4).

```bash
uv venv .venv && VIRTUAL_ENV=.venv uv pip install pytest   # once
.venv/bin/python -m pytest -q develop/incentive/tests
python3 -I develop/incentive/ridges_incentive.py research/live/2026-11-01 --set 28 --score 0.40 --cost 0.08
```

```
set 28 Database Query Engineering (share 0.25): leader 0.3800 @ $0.0924, leader age 174.1 h
to qualify: score >= 0.3914, or score >= 0.3800 with cost <= $0.0869
candidate: dperf +5.26%, dcost +13.43% -> qualified=True, units 4.07 x multiplier 6.39 = S0 25.97
note: dashboard reports multiplier 4.81 (stale observation or a later benchmark-phase end); S0 with it would be 19.55
share on approval: 46.2% of the competition = 11.54% of miner emission (shrinks only as later agents are approved)
```

Open question: for SN28 the dashboard's `time_multiplier` (4.81) implies a clock start of about
2026-10-28 16:36Z, not the leader's approval (10-25 01:34Z). Approval code uses
`NOW() - max(leader.approved_at, last benchmark-phase end)`; check `competition_benchmark_phases`
history for SN28 (not exposed publicly) or watch the next SN28 approval's stored multiplier.
