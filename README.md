# Ridges (SN62) workspace

Research on and development for Bittensor subnet 62, **Ridges**: an open competition where miners
submit a single-file software-engineering agent (`agent.py`), the platform screens and evaluates it
on hidden tasks, and emissions go to agents that beat the current leader.

```
research/   upstream repos (submodules), docs snapshot, live dashboard/chain snapshots, notes
develop/    our own code: incentive model, agent scaffold
```

Branches: `main` holds merged milestones; work happens on `research/*` and `develop/*` branches.

Everything on this machine reaches the network through the HTTP proxy in the environment
(see `research/notes/2026-11-01_environment.md`).
