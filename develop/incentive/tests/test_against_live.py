"""Check the reimplementation against the platform's stored values in the 2026-11-01 snapshot."""

import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "develop" / "incentive"))
import ridges_incentive as ri  # noqa: E402

LIVE = ROOT / "research" / "live" / "2026-11-01"
ACTIVE = (28, 29, 30)


def approved(set_id):
    return json.loads((LIVE / f"approved_{set_id}.json").read_text())


@pytest.mark.parametrize("set_id", ACTIVE)
def test_reward_score_is_units_times_multiplier(set_id):
    for a in approved(set_id):
        st = a["competition_state"]
        if st["initial_reward_score"] == 0:  # owner-hotkey baselines earn nothing
            continue
        expected = st["relative_improvement_units"] * st["time_multiplier"]
        assert math.isclose(st["initial_reward_score"], expected, rel_tol=1e-9)


@pytest.mark.parametrize("set_id", ACTIVE)
def test_units_from_deltas(set_id):
    for a in approved(set_id):
        st = a["competition_state"]
        if st["reward_basis"] != "relative" or st["performance_delta"] is None:
            continue
        dperf = st["performance_delta"]
        perf = math.log1p(dperf) / math.log1p(ri.PERF_THRESHOLD) if dperf > 0 else 0.0
        assert math.isclose(perf + ri.cost_units(st["cost_delta"]), st["relative_improvement_units"], rel_tol=1e-9)


def test_benchmark_winner_points():
    winner = next(a for a in approved(30) if a["competition_state"]["reward_basis"] == "benchmark")
    st = winner["competition_state"]
    assert math.isclose(ri.benchmark_points(st["final_score"]), st["initial_reward_score"], rel_tol=1e-9)


def test_hotkey_weights_reproduce_platform():
    comps = {c["set_id"]: c for c in json.loads((LIVE / "competitions.json").read_text())}
    platform = json.loads((LIVE / "weights.json").read_text())
    # weights.json was fetched around 07:36Z; decay over a few minutes is far below the tolerance.
    now = ri.parse_ts("2026-11-01T07:36:00Z")
    ours: dict[str, float] = {}
    for set_id in ACTIVE:
        agents = {a["agent_id"]: a for a in approved(set_id)}
        for agent_id, w in ri.competition_weights(list(agents.values()), now).items():
            hotkey = agents[agent_id]["miner_hotkey"]
            ours[hotkey] = ours.get(hotkey, 0.0) + w * comps[set_id]["raw_emission_weight"]
    assert set(ours) == set(platform)
    for hotkey, w in platform.items():
        assert ours[hotkey] == pytest.approx(w, abs=1e-4)


def test_thresholds():
    assert ri.improvement(0.515, None, 0.50, None).qualified
    assert not ri.improvement(0.514, None, 0.50, None).qualified
    assert ri.improvement(0.50, 0.094, 0.50, 0.10).qualified
    assert not ri.improvement(0.49, 0.05, 0.50, 0.10).qualified  # cheaper but worse
    assert ri.improvement(0.30, None, None, None).units == pytest.approx(30.0)
    assert ri.time_multiplier(6) == 2 and ri.time_multiplier(24) == 3
    assert ri.cost_units(1.0) == pytest.approx(1 / 0.06)
    assert ri.decay(10, 336) == pytest.approx(5)
