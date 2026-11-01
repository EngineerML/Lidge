"""Summarize one live/<date>/ snapshot: competitions, leaders, approved agents, weights vs chain.

Usage: python3 -I tools/summarize.py live/<date>
"""
import json
import sys
from pathlib import Path


def load(d: Path, name: str):
    p = d / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def main() -> None:
    d = Path(sys.argv[1])
    print(f"# Snapshot {d.name} (fetched {(d / 'FETCHED_AT').read_text().strip()})\n")

    comps = load(d, "competitions")
    active = [c for c in comps if c["emission_active"]]
    print("## Competitions\n")
    print("| set | name | state | emission share | started |")
    print("|---|---|---|---|---|")
    for c in comps:
        print(f"| {c['set_id']} | {c['name']} | {c['state']} | {c['raw_emission_weight']} | {c['start_date'][:10]} |")

    print("\n## Active competitions\n")
    for c in active:
        sid = c["set_id"]
        ns, si, price = load(d, f"network_statistics_{sid}"), load(d, f"screener_info") , load(d, f"eval_pricing_{sid}")
        print(f"### {sid} {c['name']} (share {c['raw_emission_weight']})\n")
        print(f"- leader score {ns['top_score']:.3f}, cost ${ns['top_cost']:.3f}/problem, approved {ns['last_approval'][:16]}Z")
        print(f"- time multiplier now {ns['time_multiplier']:.2f}x; to qualify: score >= {ns['top_score'] * 1.03:.3f}"
              f" or (score >= {ns['top_score']:.3f} and cost <= ${ns['top_cost'] * 0.94:.3f})")
        if price:
            print(f"- upload price ${price['price_usd']:.2f} (floor ${price['floor_usd']:.0f})")
        if si and si["set_id"] == sid:
            print(f"- screener thresholds s1 {si['screener_1_threshold']} s2 {si['screener_2_threshold']};"
                  f" avg scores s1 {si['screener_1_average_score']:.2f} s2 {si['screener_2_average_score']:.2f}"
                  f" val {si['validator_average_score']:.2f}")
        ov = load(d, f"overview_{sid}")
        if ov:
            ps = ov["performance_distribution"]["pre_screening"]
            print(f"- pre-screening: {ps['approved']} passed, {ps['rejected']} rejected")
        print("\n| agent | v | score | cost $ | units | mult | S0 | weight | approved | basis |")
        print("|---|---|---|---|---|---|---|---|---|---|")
        for a in load(d, f"approved_{sid}"):
            s = a["competition_state"]
            print(f"| {a['name']} | {a['version_num']} | {s['final_score']:.3f} | {s['average_cost_usd'] or 0:.3f} |"
                  f" {s['relative_improvement_units'] or 0:.2f} | {s['time_multiplier'] or 0:.2f} |"
                  f" {s['initial_reward_score'] or 0:.2f} | {a['reward_weight'] or 0:.4f} | {s['approved_at'][:16]} |"
                  f" {s['reward_basis']} |")
        print()

    weights = load(d, "weights")
    mg = load(d, "chain_metagraph_62")
    if weights and mg:
        by_hk = {n["hotkey"]: n for n in mg["neurons"]}
        diff = max(abs(by_hk[h]["incentive"] - w) for h, w in weights.items() if h in by_hk)
        print(f"## Weights vs chain (block {mg['block']})\n")
        print(f"- {len(weights)} hotkeys get platform weight; max |chain incentive - platform weight| = {diff:.5f}")
        total_e = sum(n["emission"] for n in mg["neurons"] if n["incentive"] > 0)
        print(f"- miner emission this tempo: {total_e:.1f} alpha across {sum(1 for n in mg['neurons'] if n['incentive'] > 0)} miners")
    subnets = load(d, "chain_subnets_list")
    if subnets:
        s = subnets["subnets"]["62"]
        print(f"- alpha price {s['price']:.6f} TAO, market cap {s['market_cap']:.0f} TAO, tempo {s['tempo']['sn_tempo']} blocks")


if __name__ == "__main__":
    main()
