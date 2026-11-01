"""General-purpose coding agent for Ridges (SN62).

Contract: agent_main({"problem_statement": str}) -> str (a unified diff of the working directory).
Inference goes through SANDBOX_PROXY_URL with the OpenRouter key from OPENROUTER_API_KEY.
Only the standard library and `requests` are used.
"""

import json
import os
import subprocess
import tempfile
import time

import requests

PROXY_URL = os.getenv("SANDBOX_PROXY_URL", "http://sandbox-proxy:80").rstrip("/")
API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("RIDGES_INFERENCE_API_KEY", "")
MODEL = os.getenv("RIDGES_AGENT_MODEL", "deepseek/deepseek-chat-v3.1")
MAX_COST_USD = float(os.getenv("RIDGES_MAX_COST_USD", "0.29"))
TIMEOUT_SEC = float(os.getenv("AGENT_TIMEOUT") or 1500)

BUDGET_RESERVE = 0.1  # stop starting new model calls once 90% of the budget is spent
TIME_RESERVE_SEC = max(30.0, 0.08 * TIMEOUT_SEC)
MAX_STEPS = 80
COMMAND_TIMEOUT_SEC = 180
OUTPUT_LIMIT = 12_000

SYSTEM_PROMPT = """You are an experienced engineer working in a terminal, in the current working directory.
You are given a task. Complete it fully by changing files in the working directory.

How to work:
- Read the task carefully. Identify exactly what must be delivered, where (file paths) and in what format.
- Explore first: list files, read the relevant code and data, check which tools and runtimes are installed.
- Make the change. Keep edits minimal and consistent with the existing code style.
- Check your work: run the code you wrote, run the project's own tests if it has them, and try cases
  beyond the obvious one. Fix what fails.
- Deliverables must be regular files inside the working directory. Give one definite answer, in exactly
  the requested format and location.
- There is no internet access and no package index; use what is already installed.
- When the work is complete and checked, call `finish` with a short summary.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Run a shell command in the working directory. Output is truncated.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file, optionally a 1-based inclusive line range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file with the given content.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "replace_in_file",
            "description": "Replace one exact, unique occurrence of old_text with new_text in a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"},
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "Call when the task is complete and verified.",
            "parameters": {
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"],
            },
        },
    },
]


def log(msg: str) -> None:
    print(f"[agent] {msg}", flush=True)


def truncate(text: str, limit: int = OUTPUT_LIMIT) -> str:
    if len(text) <= limit:
        return text
    half = limit // 2
    return f"{text[:half]}\n... [{len(text) - limit} chars omitted] ...\n{text[-half:]}"


class Workspace:
    """Tracks the working directory against a baseline kept in a private git dir,
    so the repository's own .git (if any) is never touched."""

    def __init__(self, root: str):
        self.root = os.path.abspath(root)
        self.git_dir = tempfile.mkdtemp(prefix="agent-baseline-")
        self.touched: set[str] = set()
        self._git("init", "-q")
        self._git("add", "-A")
        self._git("-c", "user.name=agent", "-c", "user.email=agent@localhost",
                  "commit", "-q", "--allow-empty", "--no-verify", "-m", "baseline")

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", f"--git-dir={self.git_dir}", f"--work-tree={self.root}", *args],
            cwd=self.root, capture_output=True, text=True, timeout=300,
        )

    def path(self, rel: str) -> str:
        full = os.path.abspath(os.path.join(self.root, rel))
        if os.path.commonpath([full, self.root]) != self.root:
            raise ValueError(f"path outside the working directory: {rel}")
        return full

    def diff(self) -> str:
        self._git("add", "-A")
        for rel in sorted(self.touched):  # files the agent wrote are kept even if .gitignore'd
            if os.path.exists(self.path(rel)):
                self._git("add", "-f", "--", rel)
        return self._git("diff", "--cached", "--binary", "HEAD").stdout


class Budget:
    def __init__(self, max_cost: float, timeout_sec: float):
        self.max_cost = max_cost
        self.spent = 0.0
        self.deadline = time.monotonic() + timeout_sec - TIME_RESERVE_SEC
        self.exhausted = False

    def time_left(self) -> float:
        return self.deadline - time.monotonic()

    def can_call(self) -> bool:
        return not self.exhausted and self.spent < self.max_cost * (1 - BUDGET_RESERVE) and self.time_left() > 0


def chat(messages: list[dict], budget: Budget) -> dict | None:
    """One non-streaming chat completion; returns the assistant message or None when we must stop."""
    for attempt in range(3):
        if not budget.can_call():
            return None
        try:
            resp = requests.post(
                f"{PROXY_URL}/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                json={"model": MODEL, "messages": messages, "tools": TOOLS, "temperature": 0.0, "max_tokens": 8000},
                timeout=max(10.0, min(300.0, budget.time_left())),
            )
        except requests.RequestException as e:
            log(f"inference error: {e}")
            time.sleep(2 * (attempt + 1))
            continue
        if resp.status_code == 429:  # out of budget for this run
            log("budget exhausted")
            budget.exhausted = True
            return None
        if resp.status_code != 200:
            log(f"inference HTTP {resp.status_code}: {resp.text[:300]}")
            time.sleep(2 * (attempt + 1))
            continue
        body = resp.json()
        budget.spent += float((body.get("usage") or {}).get("cost") or 0.0)
        choices = body.get("choices") or []
        if choices and choices[0].get("message"):
            return choices[0]["message"]
        log(f"empty completion: {str(body)[:300]}")
    return None


def run_tool(ws: Workspace, name: str, args: dict, budget: Budget) -> str:
    try:
        if name == "bash":
            limit = max(5.0, min(COMMAND_TIMEOUT_SEC, budget.time_left()))
            proc = subprocess.run(args["command"], shell=True, cwd=ws.root, capture_output=True,
                                  text=True, timeout=limit, errors="replace")
            return truncate(f"exit code {proc.returncode}\n{proc.stdout}{proc.stderr}")
        if name == "read_file":
            with open(ws.path(args["path"]), errors="replace") as f:
                lines = f.readlines()
            start = max(1, int(args.get("start_line") or 1))
            end = min(len(lines), int(args.get("end_line") or len(lines)))
            body = "".join(f"{i}\t{lines[i - 1]}" for i in range(start, end + 1))
            return truncate(f"{args['path']} ({len(lines)} lines)\n{body}")
        if name == "write_file":
            full = ws.path(args["path"])
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w") as f:
                f.write(args["content"])
            ws.touched.add(os.path.relpath(full, ws.root))
            return f"wrote {args['path']}"
        if name == "replace_in_file":
            full = ws.path(args["path"])
            with open(full) as f:
                text = f.read()
            count = text.count(args["old_text"])
            if count != 1:
                return f"error: old_text occurs {count} times; it must occur exactly once"
            with open(full, "w") as f:
                f.write(text.replace(args["old_text"], args["new_text"], 1))
            ws.touched.add(os.path.relpath(full, ws.root))
            return f"edited {args['path']}"
        return f"error: unknown tool {name}"
    except subprocess.TimeoutExpired:
        return "error: command timed out"
    except Exception as e:  # report tool failures back to the model instead of crashing
        return f"error: {type(e).__name__}: {e}"


def solve(problem: str, ws: Workspace, budget: Budget) -> None:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Task:\n\n{problem}"},
    ]
    for step in range(MAX_STEPS):
        reply = chat(messages, budget)
        if reply is None:
            return
        calls = reply.get("tool_calls") or []
        messages.append({"role": "assistant", "content": reply.get("content") or "", **({"tool_calls": calls} if calls else {})})
        if not calls:
            messages.append({"role": "user", "content": "Continue with the tools. Call `finish` when the task is done and checked."})
            continue
        for call in calls:
            name = call["function"]["name"]
            try:
                args = json.loads(call["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                args = None
            if name == "finish" and args is not None:
                log(f"finished at step {step}: {args.get('summary', '')[:200]}")
                return
            result = "error: arguments were not valid JSON" if args is None else run_tool(ws, name, args, budget)
            log(f"step {step} {name} -> {result[:120]!r}")
            messages.append({"role": "tool", "tool_call_id": call.get("id", ""), "content": result})
        if budget.time_left() < 60:
            messages.append({"role": "user", "content": "Time is almost up. Make sure the deliverable is in place, then call `finish`."})


def agent_main(input: dict) -> str:
    problem = input.get("problem_statement", "")
    budget = Budget(MAX_COST_USD, TIMEOUT_SEC)
    ws = Workspace(os.getcwd())
    try:
        solve(problem, ws, budget)
    except Exception as e:
        log(f"solve failed: {type(e).__name__}: {e}")
    patch = ws.diff()
    log(f"spent ${budget.spent:.4f}, patch {len(patch)} bytes")
    return patch
