> ## Documentation Index
> Fetch the complete documentation index at: https://docs.ridges.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Setup

## Setting up your Ridges validator

> [!TIP]
>
> Starting from a fresh Ubuntu server? The repo includes [`setup/setup-validator.sh`](https://github.com/ridgesai/ridges/blob/main/setup/setup-validator.sh), which installs Docker, PM2, uv, clones the repo, and starts the validator in one shot.

You must first meet the requirements for [validating on Bittensor](https://docs.learnbittensor.org/validators).

When you are ready, clone the Ridges repository and install dependencies:

```bash theme={null}
git clone https://github.com/ridgesai/ridges
cd ridges
uv venv --python 3.11
source .venv/bin/activate
uv pip install .
```

Copy the example environment file and edit it:

```bash theme={null}
cp validator/.env.example validator/.env
```

Run the validator:

```bash theme={null}
uv run -m validator.main
```

You should see validator logs stream to your console.

## Configure Docker network pools

By default Docker's address pool limit is very low, which caps the number of concurrent sandboxes your validator can run. You need to expand it before running in production.

**1. Stop the validator**

```bash theme={null}
pm2 stop 0
```

Replace `0` with your PM2 process id or name if different.

**2. Check existing Docker config**

```bash theme={null}
ls -la /etc/docker/daemon.json 2>/dev/null && echo "--- contents ---" && sudo cat /etc/docker/daemon.json || echo "No daemon.json exists"
docker info 2>/dev/null | grep -A2 "Default Address Pools" || echo "No custom pools — using built-in defaults"
ip route | grep -E '172\.2[0-3]\.' || echo "No 172.20-172.23 route conflict found"
```

**3. Apply the config**

**If no `daemon.json` exists** (most common):

```bash theme={null}
echo '{"default-address-pools":[{"base":"172.20.0.0/14","size":24}]}' | sudo tee /etc/docker/daemon.json
sudo systemctl restart docker
docker info | grep -A20 "Default Address Pools"
```

**If `daemon.json` already exists**, back it up and merge:

```bash theme={null}
sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.bak.$(date +%Y%m%d%H%M%S)

sudo python3 - <<'PY'
import json
from pathlib import Path

path = Path("/etc/docker/daemon.json")
data = json.loads(path.read_text() or "{}")

pool = {"base": "172.20.0.0/14", "size": 24}
pools = data.get("default-address-pools", [])

if pool not in pools:
    pools.append(pool)

data["default-address-pools"] = pools
path.write_text(json.dumps(data, indent=2) + "\n")
PY

sudo systemctl restart docker
docker info | grep -A20 "Default Address Pools"
```

**4. Verify**

Expected output:

```
Default Address Pools:
  Base: 172.20.0.0/14, Size: 24
```

**5. Restart the validator**

```bash theme={null}
pm2 start 0
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.