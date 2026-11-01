"""Dump the SN62 metagraph (lite) to live/<date>/chain_metagraph_62.json.

The chain websocket needs the HTTP proxy, so run it under proxychains with an http-proxy config:
  proxychains4 -q -f <conf> ../.venv-chain/bin/python tools/fetch_chain.py live/<date>
"""
import json
import sys
from pathlib import Path

import bittensor as bt

NETUID = 62


def main() -> None:
    out = Path(sys.argv[1])
    sub = bt.Subtensor(network="finney")
    mg = sub.metagraph(NETUID, lite=True)
    rows = []
    for uid in mg.uids.tolist():
        rows.append({
            "uid": uid,
            "hotkey": mg.hotkeys[uid],
            "coldkey": mg.coldkeys[uid],
            "stake": float(mg.S[uid]),
            "validator_permit": bool(mg.validator_permit[uid]),
            "validator_trust": float(mg.Tv[uid]),
            "incentive": float(mg.I[uid]),
            "dividends": float(mg.D[uid]),
            "emission": float(mg.E[uid]),
            "active": bool(mg.active[uid]),
        })
    data = {"netuid": NETUID, "block": int(mg.block), "n": len(rows), "neurons": rows}
    (out / "chain_metagraph_62.json").write_text(json.dumps(data, indent=1))
    print("block", data["block"], "neurons", data["n"])


if __name__ == "__main__":
    main()
