"""Ridges (SN62) reward math, reimplemented from repos/ridges/utils/incentives.py and api/incentives.py.

Answers "what does my agent need, and what would it earn" against a live snapshot:

    python3 -I develop/incentive/ridges_incentive.py research/live/<date> --set 30 --score 0.45 --cost 0.14
"""

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

PERF_THRESHOLD = 0.03
COST_THRESHOLD = 0.06
TIME_SCALE_HOURS = 6.0
HALF_LIFE_HOURS = 336.0


@dataclass(frozen=True)
class Improvement:
    qualified: bool
    performance_delta: float | None
    cost_delta: float | None
    units: float


def _meets(value: float, threshold: float) -> bool:
    return value > threshold or math.isclose(value, threshold, rel_tol=1e-9, abs_tol=1e-12)


def cost_units(cost_delta: float | None, cost_threshold: float = COST_THRESHOLD) -> float:
    if cost_delta is None or cost_delta <= 0:
        return 0.0
    cap = 1 / cost_threshold
    if cost_delta >= 1:
        return cap
    return min(math.log1p(-cost_delta) / math.log1p(-cost_threshold), cap)


def improvement(
    score: float,
    cost: float | None,
    leader_score: float | None,
    leader_cost: float | None,
    perf_threshold: float = PERF_THRESHOLD,
    cost_threshold: float = COST_THRESHOLD,
) -> Improvement:
    """Compare a candidate with the leader. No leader: the candidate sets the baseline at 100 * score."""
    if leader_score is None:
        return Improvement(True, None, None, score * 100.0)
    if leader_score == 0:
        dperf = perf_threshold if score > 0 else 0.0
    else:
        dperf = (score - leader_score) / leader_score
    dcost = None
    if cost is not None and cost >= 0 and leader_cost is not None and leader_cost > 0:
        dcost = (leader_cost - cost) / leader_cost
    perf_units = math.log1p(dperf) / math.log1p(perf_threshold) if dperf > 0 else 0.0
    qualified = _meets(dperf, perf_threshold) or (
        dcost is not None and score >= leader_score and _meets(dcost, cost_threshold)
    )
    return Improvement(qualified, dperf, dcost, perf_units + cost_units(dcost, cost_threshold))


def time_multiplier(hours_since_leader: float, scale_hours: float = TIME_SCALE_HOURS) -> float:
    return 1 + math.sqrt(max(0.0, hours_since_leader) / scale_hours)


def decay(s0: float, hours_since_approval: float, half_life_hours: float = HALF_LIFE_HOURS) -> float:
    return s0 * 2 ** (-max(0.0, hours_since_approval) / half_life_hours)


def benchmark_points(score: float, cost: float | None = None, leader_cost: float | None = None) -> float:
    """Benchmark-phase winner: 100 * score, plus cost units if cheaper than an existing leader."""
    dcost = None if cost is None or not leader_cost else (leader_cost - cost) / leader_cost
    return score * 100.0 + cost_units(dcost)


def parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def current_scores(approved: list[dict], now: datetime) -> dict[str, float]:
    """Decayed reward score per agent_id; zero-score agents (owner baselines) are left out."""
    out = {}
    for a in approved:
        st = a["competition_state"]
        s0 = st.get("initial_reward_score") or 0.0
        if s0 > 0:
            out[a["agent_id"]] = decay(s0, (now - parse_ts(st["approved_at"])).total_seconds() / 3600)
    return out


def competition_weights(approved: list[dict], now: datetime) -> dict[str, float]:
    """Each agent's fraction of one competition's share, by agent_id."""
    scores = current_scores(approved, now)
    total = sum(scores.values())
    return {k: v / total for k, v in scores.items()} if total else {}


def required_to_qualify(leader_score: float, leader_cost: float | None) -> dict[str, float | None]:
    return {
        "min_score_perf_route": leader_score * (1 + PERF_THRESHOLD),
        "min_score_cost_route": leader_score,
        "max_cost_cost_route": None if leader_cost is None else leader_cost * (1 - COST_THRESHOLD),
    }


def share_on_approval(s0: float, approved: list[dict], now: datetime) -> float:
    """Fraction of the competition for a new agent with score s0 approved at `now`.
    All scores decay at the same rate, so this fraction only shrinks when others get approved."""
    return s0 / (s0 + sum(current_scores(approved, now).values()))


def main() -> None:
    ap = argparse.ArgumentParser(description="Ridges reward calculator against a live snapshot")
    ap.add_argument("live", type=Path, help="research/live/<date> snapshot directory")
    ap.add_argument("--set", type=int, required=True, help="competition set_id")
    ap.add_argument("--score", type=float, required=True, help="expected validator consensus score (0-1)")
    ap.add_argument("--cost", type=float, help="expected average inference cost per problem, USD")
    ap.add_argument("--hours-later", type=float, default=0.0, help="approval this many hours after the snapshot")
    args = ap.parse_args()

    ns = json.loads((args.live / f"network_statistics_{args.set}.json").read_text())
    comp = next(c for c in json.loads((args.live / "competitions.json").read_text()) if c["set_id"] == args.set)
    approved = json.loads((args.live / f"approved_{args.set}.json").read_text())
    now = parse_ts((args.live / "FETCHED_AT").read_text().strip()) + timedelta(hours=args.hours_later)

    req = required_to_qualify(ns["top_score"], ns["top_cost"])
    imp = improvement(args.score, args.cost, ns["top_score"], ns["top_cost"])
    age = (now - parse_ts(ns["last_approval"])).total_seconds() / 3600
    mult = time_multiplier(age)
    s0 = imp.units * mult if imp.qualified else 0.0

    print(f"set {args.set} {comp['name']} (share {comp['raw_emission_weight']}): "
          f"leader {ns['top_score']:.4f} @ ${ns['top_cost']:.4f}, leader age {age:.1f} h")
    print(f"to qualify: score >= {req['min_score_perf_route']:.4f}, or score >= {req['min_score_cost_route']:.4f}"
          f" with cost <= ${req['max_cost_cost_route']:.4f}")
    dperf = "-" if imp.performance_delta is None else f"{imp.performance_delta:+.2%}"
    dcost = "-" if imp.cost_delta is None else f"{imp.cost_delta:+.2%}"
    print(f"candidate: dperf {dperf}, dcost {dcost} -> qualified={imp.qualified}, "
          f"units {imp.units:.2f} x multiplier {mult:.2f} = S0 {s0:.2f}")
    # Approval measures from max(leader approval, last benchmark-phase end) to NOW(); the dashboard
    # value comes from a cached leader observation and can lag behind it.
    if not args.hours_later and not math.isclose(ns["time_multiplier"], mult, rel_tol=0.01):
        print(f"note: dashboard reports multiplier {ns['time_multiplier']:.2f} (stale observation or a later "
              f"benchmark-phase end); S0 with it would be {imp.units * ns['time_multiplier']:.2f}")
    if s0:
        frac = share_on_approval(s0, approved, now)
        print(f"share on approval: {frac:.1%} of the competition = {frac * comp['raw_emission_weight']:.2%} of miner "
              f"emission (shrinks only as later agents are approved)")


if __name__ == "__main__":
    main()
