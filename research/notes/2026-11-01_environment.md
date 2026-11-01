# Environment (2026-11-01)

Host: Windows 11, WSL2 distro `Ubuntu-24.04` (kernel 6.18 WSL2), user `root`, 16 CPUs, 23 GiB RAM,
~190 GB free. Tools: git 2.43, Python 3.12.3, uv 0.13, Docker 29.9, gh (logged in as `EngineerML`).

## Network: everything goes through one HTTP proxy

- `http_proxy` / `https_proxy` (and upper-case) point at an authenticated HTTP proxy on the Windows
  host side of the WSL NAT (`172.23.144.1`, basic auth). `no_proxy=localhost,127.0.0.1,::1`.
  Credentials are not recorded here.
- apt uses the same proxy (`/etc/apt/apt.conf.d/*proxy*`, `Acquire::Retries 10`).
- git: `http.proxyAuthMethod=basic`, low-speed abort (1000 B/s for 15 s); GitHub credentials come
  from `gh auth git-credential`. Commit identity is `EngineerML`.
- HTTPS via curl, git, pip/uv works out of the box.

## Chain access (btcli / bittensor SDK)

- `.bashrc` aliases `btcli='proxychains4 -q btcli'`, but `/etc/proxychains4.conf` points at
  `socks4 127.0.0.1 9050` and **nothing listens on 9050**, so the alias does not work.
- Plain `btcli` (no proxychains) times out: the websocket to the chain does not use the env proxy.
- What works: proxychains with an **http** entry built from `$https_proxy`, kept in a private
  temp file (mode 600), and the proxy env vars **unset** for SDK scripts (otherwise the websocket
  client tries the proxy itself on top of proxychains and gets `Connection refused`):

  ```bash
  # writes /tmp/pc_http.conf: strict_chain, proxy_dns, [ProxyList] http <host> <port> <user> <pass>
  proxychains4 -q -f /tmp/pc_http.conf btcli subnets list --network finney --json-output
  env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY \
    proxychains4 -q -f /tmp/pc_http.conf .venv-chain/bin/python research/tools/fetch_chain.py live/<date>
  ```

- Set `COLUMNS=100000` for btcli JSON output, or rich wraps lines and breaks the JSON.
- `btcli subnets show` / `subnets metagraph --json-output` print nothing with btcli in
  `/home/bittensor/btcli-venv`. Use the SDK script instead (bittensor 10.5 in `.venv-chain`,
  git-ignored).

## Ridges endpoints reachable from here

| Host | Use | Status |
|---|---|---|
| `docs.ridges.ai` (`/llms.txt`, `/llms-full.txt`, `*.md`) | docs | 200 |
| `www.ridges.ai` (`/agents`, `/llms.txt`) | dashboard / Ridgeline product | 200 |
| `agent-upload.ridges.ai` | platform API behind the dashboard and CLI; public GETs | 200, rate-limited (429) |
| `platform-v2.ridges.ai` | older platform host | 403 (Cloudflare) |

The API rate-limits bursts; the proxy surfaces some 429s as `CONNECT tunnel failed, response 429`
(curl exit 56, HTTP code 000), so the fetch scripts space requests and retry both.
Cloudflare also answers `403 error code: 1010` to non-curl clients (e.g. Python urllib), so
fetch with curl.
