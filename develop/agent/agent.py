"""Problem-solving agent for Ridges (SN62).

Contract: agent_main({"problem_statement": str}) -> str, a unified diff of the working directory.
Inference goes through SANDBOX_PROXY_URL with the OpenRouter key from OPENROUTER_API_KEY.
Standard library plus `requests` only.

Design (see research/notes/2026-11-01_agent_improvements.md):
  1. structured opening: environment survey, task-path check, a recorded checklist before any edit
  2. budget and time meter shown after every tool result, tiers, and a hard pre-call guard
  3. finish gate: requirements re-checked with commands run after the gate
  4. tool-layer guards: exit code, cwd, empty output, repeated calls, failure streaks
  5. a second attempt only when the first is unverified and resources remain, then selection
  6. early elision of bulky old tool output
"""

import base64
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time

import requests

PROXY_URL = os.getenv("SANDBOX_PROXY_URL", "http://sandbox-proxy:80").rstrip("/")
API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("RIDGES_INFERENCE_API_KEY", "")
# Local runs may override these; production uses the defaults.
MODELS = [m.strip() for m in os.getenv("RIDGES_AGENT_MODELS", "openai/gpt-6.1-sol,anthropic/claude-haiku-5.5").split(",") if m.strip()]
REASONING_EFFORT = os.getenv("RIDGES_AGENT_EFFORT", "medium")
MAX_OUTPUT_TOKENS = 12000
PRICE_FALLBACK = (3.0, 15.0)  # USD per million input/output tokens, used only when a reply carries no cost

DEFAULT_TIMEOUT_SEC = 1200.0
FINAL_SAFETY_SEC = 45.0  # kept free for building the patch
BUDGET_SHARE = 0.9  # never plan to spend more than this share of the cap
RESERVE_SHARE = 0.15  # part of the plan kept for the finish gate and verification
SECOND_ATTEMPT_MIN_LEFT = 0.4

COMMAND_TIMEOUT_SEC = 60
COMMAND_TIMEOUT_MAX_SEC = 600
OUTPUT_LIMIT = 12000
MAX_JOBS = 4
ELIDE_PROMPT_TOKENS = 60000
ELIDE_KEEP_RECENT = 12
BIG_FILE_BYTES = 10 * 1024 * 1024
IMAGE_MAX_BYTES = 4 * 1024 * 1024
REPEAT_WARN, REPEAT_REFUSE = 5, 8
FAIL_STREAK_NUDGE = 5
CHECKLIST_REMINDER_EVERY = 8
MAX_STEPS = 150

EXCLUDE_PATHSPECS = [":(exclude,glob)**/__pycache__/**", ":(exclude,glob)**/*.pyc", ":(exclude,glob)**/*.pyo"]
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}

SYSTEM_PROMPT = """\
You are an expert engineer working alone in a Linux terminal session. You receive one task and a \
working directory ({workdir}). Carry the task through to a correct result that you have checked yourself.

What is kept when you finish: only the regular files inside the working directory, exactly as you leave \
them. Anything else (files elsewhere, installed packages, running processes, git commits, symlinks, empty \
folders) is lost. Put each deliverable at the exact path, with the exact name and format, that the task asks \
for. Keep experiments and helper scripts in {scratch} unless the task asks for them.

There is no network access: nothing can be downloaded or installed. Use what is on the machine, and check that \
a tool exists before relying on it.

Work in this order:
1. Understand. Read the task twice. Investigate every relevant file you discover (code, data, docs, scripts, \
existing tests, examples); do not proceed until you have examined the available resources. Check your \
premises: where you are, what the files really contain, which tools and versions exist, how the project's own \
tests run.
2. Record the checklist with record_checklist: each deliverable with its path and format, every explicit \
requirement and constraint, the assumptions you still need to verify, and how you read any ambiguous part, \
with the evidence for that reading. Files in the working directory cannot be changed before this.
3. Build. Compute results with code instead of estimating them. If the task shows examples of inputs with \
expected outputs, make your method reproduce every one of them exactly before you rely on it. Get a complete \
first version of the deliverable in place early, then improve it.
4. Check. Run what you built, look at its real output, try cases beyond the obvious one, and run the \
project's own tests if it has any. A failed check means the result is wrong: find the cause and fix it. Do \
not loosen tests or change provided inputs unless the task asks for it.
5. Finish. Call finish. You will then confirm each requirement with output from commands you run at that point.

Habits:
- Put independent tool calls in the same reply. Start slow commands with background=true and collect them with poll.
- When something surprising shows up (an unexpected file, an error, a mismatch), stop and decide whether it \
changes your plan.
- When an approach stops making progress, re-examine your assumptions instead of repeating it.
- Fix causes rather than symptoms, change only what the task needs, and keep existing behaviour the task does \
not ask you to change.
- Give one definite answer in exactly the requested format, without alternatives or hedging.
The status line after tool results shows the time and budget left; fit your work to them."""

SECOND_ATTEMPT_NOTE = """\
A colleague worked on this task before you and left the notes below. Their result could not be confirmed, so \
it was set aside and the working directory is back in its original state. Treat their notes as unverified \
hints: check each point against the task and the files yourself, and look for what they may have misread.

<colleague_notes>
{notes}
</colleague_notes>"""

JUDGE_PROMPT = """\
Two candidate results for the same task are shown as diffs of the working directory, each with the author's \
summary and the evidence they reported. Decide which one better satisfies the task.

Go through the task's requirements one by one. For each candidate, look for: a deliverable missing, misplaced \
or in the wrong format; an incomplete implementation; claims not backed by the evidence; behaviour broken \
outside what the task asked to change. Reason first, then end with exactly one line: \
"VERDICT: FIRST", "VERDICT: SECOND" or "VERDICT: TIE"."""

TIER_GUIDANCE = {
    "medium": "Converge on one approach and get a complete version of the deliverable in place.",
    "low": "Stop exploring. Finish the deliverable and verify it now.",
    "critical": "Almost out of resources: make sure the deliverable is in place and call finish.",
}

SURVEY_SCRIPT = r"""
echo "== working directory: $(pwd)"
ls -la 2>/dev/null | head -50
echo "== tree (depth 2, first 120 entries)"
find . -maxdepth 2 -not -path './.git' -not -path './.git/*' 2>/dev/null | sort | head -120
echo "== size: $(du -sh . 2>/dev/null | cut -f1)"
if git rev-parse --git-dir >/dev/null 2>&1; then echo "== git"; git log --oneline -3 2>/dev/null; git status --short 2>/dev/null | head -10; fi
echo "== tools present"
for t in python3 python pip3 pytest node npm npx tsc java javac mvn gradle go cargo rustc gcc g++ clang make cmake \
  ruby perl php Rscript julia dotnet sqlite3 psql mysql redis-cli jq rg git curl bc; do
  command -v "$t" >/dev/null 2>&1 && printf '%s ' "$t"; done; echo
python3 --version 2>&1
echo "== python packages (first 120)"
timeout 15 python3 -m pip list --format=freeze 2>/dev/null | head -120 | tr '\n' ' '; echo
echo "== machine: $(nproc 2>/dev/null) cpu, $(free -m 2>/dev/null | awk '/Mem:/{print $2" MB RAM"}')"
"""

TOOLS = [
    {"type": "function", "function": {
        "name": "bash",
        "description": "Run a bash command in a fresh shell that starts in the working directory. Returns the exit "
                       "code, the runtime and the combined output (long output is shortened in the middle). Standard "
                       "input is empty. A command still running at its timeout keeps running as a background job.",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string"},
            "timeout": {"type": "integer", "description": "Seconds to wait (default 60, at most 600)."},
            "background": {"type": "boolean", "description": "Start it as a background job and return at once."}},
            "required": ["command"]}}},
    {"type": "function", "function": {
        "name": "poll",
        "description": "Check a background job: its output so far and whether it finished. Optionally wait or stop it.",
        "parameters": {"type": "object", "properties": {
            "job": {"type": "string"},
            "wait": {"type": "integer", "description": "Seconds to wait for it (default 0, at most 120)."},
            "stop": {"type": "boolean"}},
            "required": ["job"]}}},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read a text file with line numbers, optionally a 1-based inclusive line range.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "start_line": {"type": "integer"}, "end_line": {"type": "integer"}},
            "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "Create a file or replace its whole content; parent folders are created.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                       "required": ["path", "content"]}}},
    {"type": "function", "function": {
        "name": "edit_file",
        "description": "Replace old_text with new_text in a file. old_text must match exactly and occur once, "
                       "unless replace_all is true.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"},
            "replace_all": {"type": "boolean"}},
            "required": ["path", "old_text", "new_text"]}}},
    {"type": "function", "function": {
        "name": "view_image",
        "description": "Look at a PNG, JPEG, GIF or WebP image yourself; it is shown to you after this call.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "record_checklist",
        "description": "Record or update your understanding of the task. Required before changing files in the "
                       "working directory; you can call it again whenever your understanding changes.",
        "parameters": {"type": "object", "properties": {
            "deliverables": {"type": "array", "items": {"type": "string"},
                             "description": "Each deliverable with its exact path and format."},
            "requirements": {"type": "array", "items": {"type": "string"},
                             "description": "Every explicit requirement and constraint from the task."},
            "assumptions": {"type": "array", "items": {"type": "string"},
                            "description": "Assumptions not yet verified, and how you will check them."},
            "interpretation": {"type": "string",
                               "description": "How you read any ambiguous part, and the evidence for that reading."}},
            "required": ["deliverables", "requirements"]}}},
    {"type": "function", "function": {
        "name": "finish",
        "description": "End the work when everything is in place and checked.",
        "parameters": {"type": "object", "properties": {
            "result_files": {"type": "array", "items": {"type": "string"}},
            "summary": {"type": "string"},
            "verified": {"type": "boolean", "description": "True only if checks you ran confirm every requirement."},
            "evidence": {"type": "array", "items": {"type": "string"},
                         "description": "For each requirement: the command you ran and what it showed."}},
            "required": ["result_files", "summary", "verified"]}}},
]


def log(msg: str) -> None:
    try:
        print(f"[agent] {msg}", flush=True)
    except Exception:
        pass


def shorten(text: str, limit: int = OUTPUT_LIMIT) -> str:
    if len(text) <= limit:
        return text
    half = limit // 2
    return f"{text[:half]}\n[... {len(text) - limit} characters omitted ...]\n{text[-half:]}"


def fmt_secs(s: float) -> str:
    s = max(0, int(s))
    return f"{s // 60}m{s % 60:02d}s"


def child_env() -> dict:
    env = dict(os.environ)
    for key in ("OPENROUTER_API_KEY", "RIDGES_INFERENCE_API_KEY"):
        env.pop(key, None)
    env.update({"PAGER": "cat", "GIT_PAGER": "cat", "TERM": "dumb", "DEBIAN_FRONTEND": "noninteractive",
                "PYTHONUNBUFFERED": "1", "PYTHONDONTWRITEBYTECODE": "1", "GIT_TERMINAL_PROMPT": "0",
                "PIP_NO_INPUT": "1"})
    return env


# ---------------------------------------------------------------- resources

class Meter:
    """Spending and time for the whole run, shared by every attempt."""

    def __init__(self, cap_usd: float, timeout_sec: float):
        self.cap = max(0.0, cap_usd) * BUDGET_SHARE
        self.start = time.time()
        self.end = self.start + timeout_sec - FINAL_SAFETY_SEC
        self.reserve_sec = max(60.0, 0.12 * timeout_sec)
        self.spent = 0.0
        self.last_cost = 0.0
        self.calls = 0
        self.exhausted = False

    def time_left(self) -> float:
        return self.end - time.time()

    def budget_left(self) -> float:
        return max(0.0, self.cap - self.spent)

    def fraction_left(self) -> float:
        span = max(1.0, self.end - self.start)
        budget = self.budget_left() / self.cap if self.cap > 0 else 0.0
        return max(0.0, min(budget, self.time_left() / span))

    def tier(self) -> str:
        f = self.fraction_left()
        return "high" if f >= 0.7 else "medium" if f >= 0.3 else "low" if f >= 0.1 else "critical"

    def can_call(self, use_reserve: bool = False) -> bool:
        if self.exhausted:
            return False
        limit = self.cap if use_reserve else self.cap * (1 - RESERVE_SHARE)
        if self.spent + max(self.last_cost * 1.5, 0.002) > limit:
            return False
        return self.time_left() > (15.0 if use_reserve else self.reserve_sec)

    def book(self, usage: dict) -> None:
        cost = usage.get("cost")
        if not isinstance(cost, (int, float)):
            cost = ((usage.get("prompt_tokens") or 0) * PRICE_FALLBACK[0]
                    + (usage.get("completion_tokens") or 0) * PRICE_FALLBACK[1]) / 1e6
        self.spent += float(cost)
        self.last_cost = float(cost)
        self.calls += 1

    def status(self) -> str:
        pct = int(100 * self.budget_left() / self.cap) if self.cap > 0 else 0
        return f"[time left {fmt_secs(self.time_left())} | budget left {pct}% | {self.tier()}]"


class LLM:
    """Chat completions through the sandbox proxy, with model fallback and budget awareness."""

    def __init__(self, meter: Meter):
        self.meter = meter
        self.model_index = 0
        self.send_reasoning = bool(REASONING_EFFORT)
        self.last_prompt_tokens = 0
        self.context_too_long = False

    @property
    def model(self) -> str:
        return MODELS[self.model_index]

    def chat(self, messages: list, tools: list | None = None, use_reserve: bool = False,
             max_tokens: int = MAX_OUTPUT_TOKENS) -> dict | None:
        self.context_too_long = False
        for attempt in range(5):
            if not self.meter.can_call(use_reserve):
                return None
            payload = {"model": self.model, "messages": messages, "max_tokens": max_tokens}
            if tools:
                payload["tools"] = tools
            if self.send_reasoning:
                payload["reasoning"] = {"effort": REASONING_EFFORT}
            try:
                resp = requests.post(
                    f"{PROXY_URL}/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                    json=payload, timeout=max(15.0, min(300.0, self.meter.time_left())))
            except requests.RequestException as e:
                log(f"inference error: {type(e).__name__}: {e}")
                time.sleep(min(8, 2 ** attempt))
                continue
            text = resp.text[:500].lower()
            if resp.status_code in (402, 429) and ("budget" in text or "cost" in text or resp.status_code == 402):
                log("proxy reports the budget is exhausted")
                self.meter.exhausted = True
                return None
            if resp.status_code == 429 or resp.status_code >= 500:
                time.sleep(min(8, 2 ** attempt))
                continue
            if resp.status_code != 200:
                log(f"inference HTTP {resp.status_code}: {text[:200]}")
                if any(w in text for w in ("context", "too long", "too many tokens", "maximum")):
                    self.context_too_long = True
                    return None
                if self.send_reasoning and "reasoning" in text:
                    self.send_reasoning = False
                    continue
                if self.model_index + 1 < len(MODELS):
                    self.model_index += 1
                    log(f"switching to {self.model}")
                    continue
                return None
            try:
                body = resp.json()
            except ValueError:
                continue
            self.meter.book(body.get("usage") or {})
            self.last_prompt_tokens = int((body.get("usage") or {}).get("prompt_tokens") or 0)
            choices = body.get("choices") or []
            if choices and isinstance(choices[0].get("message"), dict) and not choices[0].get("error"):
                return choices[0]["message"]
            log(f"empty or failed completion: {str(body)[:200]}")
        return None


# ---------------------------------------------------------------- workspace

class Workspace:
    """Tracks the working directory against a baseline in a private git dir.

    The repository's own .git is never touched, and the diff works in folders that are not repositories."""

    def __init__(self, root: str):
        self.root = os.path.realpath(root)
        self.git_dir = tempfile.mkdtemp(prefix="agent-base-")
        self.backup_dir = os.path.join(self.git_dir, "untracked-originals")
        self.touched: set[str] = set()
        self.backed_up: set[str] = set()
        self.nested = self._find_nested_repos()
        self.base = None
        self._git("init", "-q")
        self._stage()
        out = self._git("-c", "user.name=agent", "-c", "user.email=agent@localhost", "commit", "-q",
                        "--allow-empty", "--no-verify", "-m", "baseline")
        if out.returncode == 0:
            self.base = self._git("rev-parse", "HEAD").stdout.strip()
        else:
            log(f"baseline commit failed: {out.stderr[:200]}")

    def _git(self, *args: str, index: str | None = None, input_text: str | None = None) -> subprocess.CompletedProcess:
        env = child_env()
        if index:
            env["GIT_INDEX_FILE"] = index
        try:
            return subprocess.run(["git", f"--git-dir={self.git_dir}", f"--work-tree={self.root}", *args],
                                  cwd=self.root, capture_output=True, text=True, timeout=300, env=env,
                                  input=input_text, errors="replace")
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(args, 124, "", "timeout")

    def _find_nested_repos(self) -> list[str]:
        found, seen = [], 0
        for top, dirs, _files in os.walk(self.root):
            seen += 1
            if seen > 50000:
                break
            if top != self.root and ".git" in os.listdir(top):
                found.append(os.path.relpath(top, self.root))
                dirs[:] = []
                continue
            dirs[:] = [d for d in dirs if d != ".git" and not os.path.islink(os.path.join(top, d))]
        return found

    def _pathspecs(self) -> list[str]:
        return [".", *EXCLUDE_PATHSPECS, *[f":(exclude){p}" for p in self.nested]]

    def _stage(self, keep: set[str] | None = None) -> None:
        self._git("add", "-A", "--", *self._pathspecs())
        for rel in sorted(self.touched):
            full = os.path.join(self.root, rel)
            if os.path.isfile(full) and not os.path.islink(full):
                self._git("add", "-f", "--", rel)
        if self.base is None:
            return
        keep = keep or set()
        # Drop entries that would not survive as regular files: symlinks, nested repositories, huge new files.
        listing = self._git("ls-files", "-s").stdout
        drop = []
        for line in listing.splitlines():
            meta, _, path = line.partition("\t")
            mode = meta.split(" ")[0] if meta else ""
            if mode in ("120000", "160000"):
                drop.append(path)
            elif path not in keep:
                full = os.path.join(self.root, path)
                if os.path.isfile(full) and os.path.getsize(full) > BIG_FILE_BYTES and self._is_new(path):
                    drop.append(path)
        for path in drop:
            self._git("rm", "-q", "--cached", "--", path)
            if self._git("cat-file", "-e", f"{self.base}:{path}").returncode == 0:
                self._git("reset", "-q", self.base, "--", path)

    def before_write(self, rel: str) -> None:
        """Keep a copy of a pre-existing file the baseline does not track (e.g. git-ignored), so restore() can
        bring it back."""
        if rel in self.touched or rel in self.backed_up or self.base is None:
            return
        full = os.path.join(self.root, rel)
        if os.path.isfile(full) and not os.path.islink(full) and self._is_new(rel):
            dest = os.path.join(self.backup_dir, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(full, dest)
            self.backed_up.add(rel)

    def _is_new(self, path: str) -> bool:
        return self._git("cat-file", "-e", f"{self.base}:{path}").returncode != 0

    def changes(self, keep: set[str] | None = None) -> list[tuple[str, str]]:
        if self.base is None:
            return []
        self._stage(keep)
        out = self._git("diff", "--cached", "--name-status", self.base).stdout
        return [tuple(line.split("\t", 1)) for line in out.splitlines() if "\t" in line]

    def diff(self, keep: set[str] | None = None) -> str:
        if self.base is None:
            return ""
        self._stage(keep)
        patch = self._git("diff", "--cached", "--binary", self.base).stdout
        if patch and not self.applies(patch):
            log("warning: the patch does not apply cleanly to the baseline")
        return patch

    def applies(self, patch: str) -> bool:
        index = os.path.join(self.git_dir, "check.idx")
        self._git("read-tree", self.base, index=index)
        result = self._git("apply", "--cached", "--check", "-", index=index, input_text=patch)
        return result.returncode == 0

    def restore(self) -> None:
        """Put the working directory back to the baseline (tracked content; files created since are removed)."""
        if self.base is None:
            return
        self._stage()
        added = self._git("diff", "--cached", "--name-only", "--diff-filter=A", self.base).stdout.splitlines()
        for rel in added:
            full = os.path.join(self.root, rel)
            try:
                if os.path.islink(full) or os.path.isfile(full):
                    os.remove(full)
            except OSError:
                pass
        self._git("checkout", "-f", self.base, "--", ".")
        self._git("read-tree", self.base)
        for rel in self.backed_up:
            src, dest = os.path.join(self.backup_dir, rel), os.path.join(self.root, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(src, dest)
        self.touched.clear()


# ---------------------------------------------------------------- background jobs

class Job:
    def __init__(self, name: str, command: str, cwd: str, scratch: str):
        self.name = name
        self.started = time.time()
        fd, self.path = tempfile.mkstemp(prefix="job_", suffix=".out", dir=scratch)
        self.sink = os.fdopen(fd, "wb")
        self.proc = subprocess.Popen(["bash", "-c", command], cwd=cwd, stdin=subprocess.DEVNULL,
                                     stdout=self.sink, stderr=subprocess.STDOUT, start_new_session=True,
                                     env=child_env())

    def wait(self, seconds: float) -> bool:
        try:
            self.proc.wait(timeout=max(0.1, seconds))
            return True
        except subprocess.TimeoutExpired:
            return False

    def output(self) -> str:
        try:
            self.sink.flush()
            with open(self.path, "rb") as fh:
                return fh.read().decode("utf-8", errors="replace")
        except OSError:
            return ""

    def stop(self) -> None:
        if self.proc.poll() is None:
            try:
                os.killpg(self.proc.pid, signal.SIGKILL)
            except OSError:
                pass
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
        try:
            self.sink.close()
        except OSError:
            pass


# ---------------------------------------------------------------- one attempt

CWD_MARK = "__agent_cwd__"


def mentioned_paths(task: str, root: str) -> list[str]:
    """Paths and file names the task mentions, with whether they exist (a premise check)."""
    cands = re.findall(r"`([^`\n]{1,160})`", task)
    cands += re.findall(r"(?<![\w/.-])((?:/|\./)?[\w.-]+(?:/[\w.-]+)+|[\w-]{2,}\.[A-Za-z][A-Za-z0-9]{0,4})(?![\w/])", task)
    lines, seen = [], set()
    for c in cands:
        c = c.strip().rstrip(".,:;")
        if not c or " " in c or c in seen or len(lines) >= 25 or c.startswith(("http:", "https:")):
            continue
        seen.add(c)
        full = c if os.path.isabs(c) else os.path.join(root, c)
        if os.path.isdir(full):
            lines.append(f"  {c}: folder exists")
        elif os.path.isfile(full):
            lines.append(f"  {c}: file exists ({os.path.getsize(full)} bytes)")
        elif "/" in c or "." in c:
            lines.append(f"  {c}: not found")
    return lines


class Attempt:
    def __init__(self, label: str, task: str, ws: Workspace, llm: LLM, meter: Meter, scratch: str,
                 colleague_notes: str | None = None):
        self.label = label
        self.task = task
        self.ws = ws
        self.llm = llm
        self.meter = meter
        self.scratch = scratch
        self.colleague_notes = colleague_notes
        self.messages: list = []
        self.checklist: dict | None = None
        self.jobs: dict[str, Job] = {}
        self.job_seq = 0
        self.pending_images: list = []
        self.finished = False
        self.verified = False
        self.summary = ""
        self.evidence: list[str] = []
        self.result_files: list[str] = []
        self.gate_rounds = 0
        self.commands_since_gate = 0
        self.last_call_key = None
        self.repeat_count = 0
        self.fail_streak = 0
        self.steps = 0
        self.last_tier = "high"
        self.milestone_nudged = False

    # ---- paths

    def _path(self, p: str) -> str:
        p = os.path.expanduser(str(p).strip())
        return os.path.normpath(p if os.path.isabs(p) else os.path.join(self.ws.root, p))

    def _inside(self, full: str) -> str | None:
        rel = os.path.relpath(full, self.ws.root)
        return None if rel == ".." or rel.startswith("../") else rel

    # ---- tools

    def tool_bash(self, args: dict) -> str:
        command = str(args.get("command") or "")
        if not command.strip():
            return "error: empty command"
        self.commands_since_gate += 1
        if args.get("background"):
            return self._start_job(command, wait=0)
        limit = int(args.get("timeout") or COMMAND_TIMEOUT_SEC)
        limit = max(1, min(limit, COMMAND_TIMEOUT_MAX_SEC, int(max(5, self.meter.time_left() / 2))))
        return self._start_job(command, wait=limit)

    def _start_job(self, command: str, wait: float) -> str:
        running = [j for j in self.jobs.values() if j.proc.poll() is None]
        if len(running) >= MAX_JOBS:
            return f"error: {len(running)} background jobs are still running; poll or stop one first"
        self.job_seq += 1
        wrapped = f"{command}\n__rc=$?\nprintf '\\n{CWD_MARK}%s\\n' \"$PWD\"\nexit $__rc"
        job = Job(f"job{self.job_seq}", wrapped, self.ws.root, self.scratch)
        if wait <= 0:
            self.jobs[job.name] = job
            return f"started background job {job.name}; collect it with poll"
        if job.wait(wait):
            report = self._report(job, finished=True)
            job.stop()
            return report
        self.jobs[job.name] = job
        return self._report(job, finished=False)

    def _report(self, job: Job, finished: bool) -> str:
        out = job.output()
        cwd = None
        m = re.search(rf"\n?{CWD_MARK}(.*)\n?$", out)
        if m:
            cwd = m.group(1).strip()
            out = out[:m.start()]
        elapsed = time.time() - job.started
        if not finished:
            head = f"still running after {elapsed:.0f}s as background job {job.name} (use poll)"
        else:
            code = job.proc.returncode
            head = f"exit {code}" + (f", {elapsed:.0f}s" if elapsed >= 5 else "")
            self.fail_streak = self.fail_streak + 1 if code else 0
        if cwd and os.path.realpath(cwd) != self.ws.root:
            head += f", ended in {cwd}"
        body = out.strip("\n")
        return f"{head}\n{shorten(body)}" if body else f"{head}\n(no output)"

    def tool_poll(self, args: dict) -> str:
        job = self.jobs.get(str(args.get("job") or ""))
        if job is None:
            return "error: unknown job; known jobs: " + (", ".join(self.jobs) or "none")
        if args.get("stop"):
            job.stop()
            self.jobs.pop(job.name, None)
            return f"stopped {job.name}\n{shorten(job.output())}"
        wait = max(0, min(int(args.get("wait") or 0), 120, int(max(0, self.meter.time_left() - 10))))
        finished = job.wait(wait) if wait else job.proc.poll() is not None
        report = self._report(job, finished)
        if finished:
            job.stop()
            self.jobs.pop(job.name, None)
        return report

    def tool_read_file(self, args: dict) -> str:
        full = self._path(args.get("path", ""))
        if not os.path.isfile(full):
            return f"error: {full} is not a file"
        with open(full, "rb") as fh:
            data = fh.read(4 * 1024 * 1024)
        if b"\0" in data[:8192]:
            return f"error: {full} looks binary ({os.path.getsize(full)} bytes); inspect it with bash"
        lines = data.decode("utf-8", errors="replace").splitlines()
        start = max(1, int(args.get("start_line") or 1))
        end = min(len(lines), int(args.get("end_line") or len(lines)))
        body = "\n".join(f"{i}\t{lines[i - 1]}" for i in range(start, end + 1))
        return shorten(f"{full} ({len(lines)} lines)\n{body}")

    def _check_write(self, full: str) -> str | None:
        rel = self._inside(full)
        if rel is not None and self.checklist is None:
            return ("error: record your understanding with record_checklist before changing files in the "
                    "working directory")
        if os.path.islink(full):
            return "error: that path is a symlink; deliverables must be regular files"
        if rel is not None:
            self.ws.before_write(rel)
        return None

    def _after_write(self, full: str) -> str:
        rel = self._inside(full)
        if rel is not None:
            self.ws.touched.add(rel)
        ext = os.path.splitext(full)[1].lower()
        check = None
        if ext == ".py":
            check = ["python3", "-m", "py_compile", full]
        elif ext in (".sh", ".bash"):
            check = ["bash", "-n", full]
        elif ext == ".json":
            try:
                with open(full) as fh:
                    json.load(fh)
            except Exception as e:
                return f"\nnote: the file is not valid JSON: {e}"
            return ""
        elif ext in (".js", ".mjs", ".cjs") and shutil.which("node"):
            check = ["node", "--check", full]
        if check:
            try:
                r = subprocess.run(check, capture_output=True, text=True, timeout=20, env=child_env())
                if r.returncode != 0:
                    return f"\nnote: syntax check failed:\n{shorten((r.stdout + r.stderr).strip(), 2000)}"
            except (OSError, subprocess.TimeoutExpired):
                pass
        return ""

    def tool_write_file(self, args: dict) -> str:
        full = self._path(args.get("path", ""))
        problem = self._check_write(full)
        if problem:
            return problem
        content = args.get("content")
        if not isinstance(content, str):
            return "error: content must be a string"
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as fh:
            fh.write(content)
        return f"wrote {len(content)} characters to {full}{self._after_write(full)}"

    def tool_edit_file(self, args: dict) -> str:
        full = self._path(args.get("path", ""))
        problem = self._check_write(full)
        if problem:
            return problem
        if not os.path.isfile(full):
            return f"error: {full} does not exist"
        with open(full, errors="replace") as fh:
            text = fh.read()
        old, new = str(args.get("old_text", "")), str(args.get("new_text", ""))
        count = text.count(old) if old else 0
        if count == 0:
            return "error: old_text was not found; read the file again and copy the text exactly"
        if count > 1 and not args.get("replace_all"):
            return f"error: old_text occurs {count} times; add surrounding lines or set replace_all"
        with open(full, "w") as fh:
            fh.write(text.replace(old, new) if args.get("replace_all") else text.replace(old, new, 1))
        return f"edited {full} ({count} replacement{'s' if count > 1 else ''}){self._after_write(full)}"

    def tool_view_image(self, args: dict) -> str:
        full = self._path(args.get("path", ""))
        mime = IMAGE_TYPES.get(os.path.splitext(full)[1].lower())
        if mime is None or not os.path.isfile(full):
            return "error: not an existing PNG, JPEG, GIF or WebP file"
        if os.path.getsize(full) > IMAGE_MAX_BYTES:
            return "error: image larger than 4 MB; make a smaller copy in scratch first"
        with open(full, "rb") as fh:
            data = base64.b64encode(fh.read()).decode("ascii")
        self.pending_images.append((full, {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}}))
        return f"{full} will be shown to you next"

    def tool_record_checklist(self, args: dict) -> str:
        def items(key):
            v = args.get(key) or []
            return [str(x) for x in v] if isinstance(v, list) else [str(v)]
        self.checklist = {"deliverables": items("deliverables"), "requirements": items("requirements"),
                          "assumptions": items("assumptions"), "interpretation": str(args.get("interpretation") or "")}
        if not self.checklist["deliverables"]:
            self.checklist = None
            return "error: list at least one deliverable with its path and format"
        return "checklist recorded. Verify the open assumptions before relying on them."

    def checklist_text(self, compact: bool = False) -> str:
        if not self.checklist:
            return "(no checklist recorded)"
        c = self.checklist
        if compact:
            return "Deliverables: " + "; ".join(c["deliverables"]) + " | Requirements: " + "; ".join(c["requirements"])
        parts = ["Deliverables:", *[f"- {d}" for d in c["deliverables"]], "Requirements:",
                 *[f"- {r}" for r in c["requirements"]]]
        if c["assumptions"]:
            parts += ["Assumptions:", *[f"- {a}" for a in c["assumptions"]]]
        if c["interpretation"]:
            parts += ["Interpretation: " + c["interpretation"]]
        return "\n".join(parts)

    def tool_finish(self, args: dict) -> str:
        files = args.get("result_files") or []
        files = [files] if isinstance(files, str) else files if isinstance(files, list) else []
        problems, rels = [], []
        for f in files:
            full = self._path(f)
            rel = self._inside(full)
            if rel is None:
                problems.append(f"{full} is outside the working directory and would be lost")
            elif os.path.islink(full):
                problems.append(f"{rel} is a symlink; make it a regular file")
            elif not os.path.exists(full):
                problems.append(f"{rel} does not exist")
            elif os.path.isdir(full) and not os.listdir(full):
                problems.append(f"{rel} is an empty folder")
            else:
                rels.append(rel)
        changed = self.ws.changes(set(rels))
        if not changed:
            problems.append("nothing in the working directory has changed yet")
        self.result_files = rels
        self.summary = str(args.get("summary") or "")
        self.evidence = [str(e) for e in (args.get("evidence") or [])] if isinstance(args.get("evidence"), list) else []
        self.verified = bool(args.get("verified"))
        if problems:
            return "Not finished:\n- " + "\n- ".join(problems)
        listing = "\n".join(f"  {s} {p}" for s, p in changed[:60])
        if self.gate_rounds == 0 and self.meter.can_call(use_reserve=True):
            self.gate_rounds = 1
            self.commands_since_gate = 0
            return ("Before this is final, confirm it.\n\nChanged files (A added, M modified, D deleted):\n"
                    f"{listing}\n\nThe task again:\n<task>\n{self.task.strip()}\n</task>\n\nYour checklist:\n"
                    f"{self.checklist_text()}\n\nRun the checks now: for every deliverable and requirement, run a "
                    "command that shows it is met (file at the exact path and format, outputs reproduced, examples "
                    "matched, the project's tests). Do not rely on earlier results. Remove scratch files from the "
                    "working directory that the task did not ask for. Fix anything that fails, then call finish "
                    "again with verified and the evidence (command and what it showed) for each requirement.")
        if self.commands_since_gate == 0 and self.gate_rounds < 3 and self.meter.can_call(use_reserve=True):
            self.gate_rounds += 1
            return "Run the checks first: no command has been run since the request to confirm the result."
        self.finished = True
        return "Finished."

    # ---- loop

    def run_tool(self, name: str, raw) -> str:
        try:
            args = json.loads(raw) if isinstance(raw, str) and raw.strip() else (raw or {})
            if not isinstance(args, dict):
                raise ValueError("arguments must be an object")
        except Exception as e:
            return f"error: arguments are not valid JSON ({e})"
        key = name + json.dumps(args, sort_keys=True)[:2000]
        self.repeat_count = self.repeat_count + 1 if key == self.last_call_key else 1
        self.last_call_key = key
        if self.repeat_count >= REPEAT_REFUSE and name != "poll":
            return "error: this exact call has been repeated many times without progress; change your approach"
        handler = getattr(self, "tool_" + name, None) if name.isidentifier() else None
        if handler is None:
            return f"error: unknown tool {name!r}"
        try:
            result = handler(args)
        except Exception as e:
            result = f"error: {type(e).__name__}: {e}"
        if self.repeat_count >= REPEAT_WARN and name != "poll":
            result += "\nnote: you have repeated this exact call several times; consider a different approach."
        return result

    def opening(self) -> str:
        try:
            survey = subprocess.run(["bash", "-c", SURVEY_SCRIPT], cwd=self.ws.root, capture_output=True,
                                    text=True, timeout=40, env=child_env(), errors="replace").stdout
        except subprocess.TimeoutExpired:
            survey = "(survey timed out)"
        parts = [f"<task>\n{self.task.strip()}\n</task>",
                 f"Working directory: {self.ws.root}\nScratch folder: {self.scratch}\n"
                 f"Time available: about {fmt_secs(self.meter.time_left())}.",
                 "Overview of the working directory and the machine:\n" + shorten(survey, 9000)]
        paths = mentioned_paths(self.task, self.ws.root)
        if paths:
            parts.append("Paths and files named in the task:\n" + "\n".join(paths))
        if self.ws.nested:
            parts.append("Note: these folders are separate git repositories and changes inside them are not kept: "
                         + ", ".join(self.ws.nested[:10]))
        if self.colleague_notes:
            parts.append(SECOND_ATTEMPT_NOTE.format(notes=self.colleague_notes))
        return "\n\n".join(parts)

    def elide(self, keep_recent: int = ELIDE_KEEP_RECENT) -> None:
        cut = max(2, len(self.messages) - keep_recent)
        for m in self.messages[2:cut]:
            if m.get("role") == "tool" and isinstance(m.get("content"), str) and len(m["content"]) > 1200:
                c = m["content"]
                m["content"] = c[:500] + "\n[... older output removed ...]\n" + c[-300:]
            elif m.get("role") == "user" and isinstance(m.get("content"), list):
                m["content"] = [p if p.get("type") == "text" else {"type": "text", "text": "[image removed]"}
                                for p in m["content"]]

    def status_note(self) -> str:
        note = self.meter.status()
        tier = self.meter.tier()
        if tier != self.last_tier and tier in TIER_GUIDANCE:
            note += " " + TIER_GUIDANCE[tier]
        self.last_tier = tier
        if self.checklist and self.steps and self.steps % CHECKLIST_REMINDER_EVERY == 0:
            note += "\n[checklist] " + self.checklist_text(compact=True)
        if self.fail_streak >= FAIL_STREAK_NUDGE:
            note += ("\nSeveral commands in a row have failed. List your current assumptions and check the one you "
                     "have not verified before trying again.")
            self.fail_streak = 0
        return note

    def maybe_milestone(self) -> None:
        if self.milestone_nudged or self.meter.fraction_left() > 0.5:
            return
        self.milestone_nudged = True
        if not self.ws.changes():
            self.messages.append({"role": "user", "content": (
                "Half of the available time or budget is used and the working directory is unchanged. Put a "
                "complete first version of the deliverable at the exact path now, then keep improving and checking it.")})

    def run(self) -> "Attempt":
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT.format(workdir=self.ws.root, scratch=self.scratch)},
                         {"role": "user", "content": self.opening()}]
        idle = 0
        while not self.finished and self.steps < MAX_STEPS:
            if self.llm.last_prompt_tokens > ELIDE_PROMPT_TOKENS:
                self.elide()
                self.llm.last_prompt_tokens = 0
            finishing = self.gate_rounds > 0
            msg = self.llm.chat(self.messages, TOOLS, use_reserve=finishing)
            if msg is None and self.llm.context_too_long:
                self.elide(keep_recent=6)
                msg = self.llm.chat(self.messages, TOOLS, use_reserve=finishing)
            if msg is None:
                log(f"attempt {self.label}: stopping (no reply or out of resources)")
                break
            self.steps += 1
            calls = [c for c in (msg.get("tool_calls") or []) if isinstance(c, dict)]
            entry = {"role": "assistant", "content": msg.get("content") or ""}
            if calls:
                entry["tool_calls"] = []
                for i, c in enumerate(calls):
                    fn = c.get("function") or {}
                    arguments = fn.get("arguments") or "{}"
                    entry["tool_calls"].append({
                        "id": str(c.get("id") or f"call_{self.steps}_{i}"), "type": "function",
                        "function": {"name": str(fn.get("name") or ""),
                                     "arguments": arguments if isinstance(arguments, str) else json.dumps(arguments)}})
            self.messages.append(entry)
            if not calls:
                idle += 1
                if idle >= 3:
                    break
                self.messages.append({"role": "user", "content": "Continue with the tools; call finish when the "
                                      "result is in place and checked. " + self.meter.status()})
                continue
            idle = 0
            for i, call in enumerate(entry["tool_calls"]):
                fn = call["function"]
                result = "not run: the work is already finished" if self.finished else self.run_tool(fn["name"], fn["arguments"])
                if i == len(entry["tool_calls"]) - 1:
                    result += "\n" + self.status_note()
                log(f"{self.label}{self.steps} {fn['name']} -> {result[:100]!r}")
                self.messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})
            if self.pending_images:
                parts = []
                for full, part in self.pending_images:
                    parts += [{"type": "text", "text": f"{full}:"}, part]
                self.messages.append({"role": "user", "content": parts})
                self.pending_images = []
            self.maybe_milestone()
            if not self.meter.can_call(use_reserve=False) and not finishing and not self.finished:
                self.messages.append({"role": "user", "content": (
                    "Resources are nearly used up. Make sure the deliverable is in place and call finish now.")})
                self.gate_rounds = max(self.gate_rounds, 1)
        for job in list(self.jobs.values()):
            job.stop()
        self.jobs.clear()
        return self

    def notes(self) -> str:
        return (self.checklist_text() + f"\nSummary of their result: {self.summary or '(none)'}"
                + ("\nTheir evidence:\n" + "\n".join(f"- {e}" for e in self.evidence) if self.evidence else ""))


# ---------------------------------------------------------------- selection and entry point

def judge(llm: LLM, task: str, first: tuple, second: tuple) -> str:
    """One pairwise judgment; returns FIRST, SECOND or TIE."""
    def block(name, cand):
        att, patch = cand
        return (f"<{name}>\nSummary: {att.summary or '(none)'}\nVerified by author: {att.verified}\nEvidence:\n"
                + ("\n".join(f"- {e}" for e in att.evidence) or "(none)") + f"\nDiff:\n{shorten(patch, 9000)}\n</{name}>")
    content = f"<task>\n{task.strip()}\n</task>\n\n{block('first', first)}\n\n{block('second', second)}"
    msg = llm.chat([{"role": "system", "content": JUDGE_PROMPT}, {"role": "user", "content": content}],
                   tools=None, use_reserve=True, max_tokens=4000)
    m = re.search(r"VERDICT:\s*(FIRST|SECOND|TIE)", (msg or {}).get("content") or "")
    return m.group(1) if m else "TIE"


def choose(llm: LLM, task: str, a: tuple, b: tuple) -> tuple:
    (att_a, patch_a), (att_b, patch_b) = a, b
    if not patch_b.strip():
        return a
    if not patch_a.strip():
        return b
    if att_a.finished and att_a.verified and not (att_b.finished and att_b.verified):
        return a
    if att_b.finished and att_b.verified and not (att_a.finished and att_a.verified):
        return b
    v1 = judge(llm, task, a, b)
    v2 = judge(llm, task, b, a)
    log(f"judge: A-first {v1}, B-first {v2}")
    if v1 == "SECOND" and v2 == "FIRST":
        return b
    return a


def scratch_dir(workdir: str) -> str:
    root = os.path.realpath(workdir)
    for base in ("/tmp", tempfile.gettempdir(), "/var/tmp"):
        real = os.path.realpath(base)
        if real == root or real.startswith(root.rstrip("/") + "/"):
            continue
        try:
            return tempfile.mkdtemp(prefix="agent-scratch-", dir=base)
        except OSError:
            continue
    return tempfile.mkdtemp(prefix="agent-scratch-")


def solve(task: str, workdir: str) -> str:
    try:
        timeout = float(os.getenv("AGENT_TIMEOUT") or DEFAULT_TIMEOUT_SEC)
    except ValueError:
        timeout = DEFAULT_TIMEOUT_SEC
    try:
        cap = float(os.getenv("RIDGES_MAX_COST_USD") or 0.29)
    except ValueError:
        cap = 0.29
    meter = Meter(cap, timeout)
    llm = LLM(meter)
    ws = Workspace(workdir)
    _CURRENT["ws"] = ws
    scratch = scratch_dir(workdir)
    log(f"start: model {llm.model}, timeout {timeout:.0f}s, budget ${cap:.2f}, workdir {ws.root}")

    a = Attempt("A", task, ws, llm, meter, scratch).run()
    patch_a = ws.diff(set(a.result_files))
    log(f"attempt A: finished={a.finished} verified={a.verified} patch={len(patch_a)}B spent=${meter.spent:.4f}")
    best = (a, patch_a)

    a_confirmed = a.finished and a.verified and bool(patch_a.strip())
    if (not a_confirmed and not meter.exhausted and ws.base is not None
            and meter.fraction_left() >= SECOND_ATTEMPT_MIN_LEFT):
        ws.restore()
        b = Attempt("B", task, ws, llm, meter, scratch, colleague_notes=a.notes()).run()
        patch_b = ws.diff(set(b.result_files))
        log(f"attempt B: finished={b.finished} verified={b.verified} patch={len(patch_b)}B spent=${meter.spent:.4f}")
        best = choose(llm, task, best, (b, patch_b))
        log(f"selected attempt {best[0].label}")
    log(f"done: ${meter.spent:.4f} over {meter.calls} calls, {time.time() - meter.start:.0f}s")
    return best[1]


_CURRENT: dict = {}


def agent_main(input: dict) -> str:
    task = str((input or {}).get("problem_statement") or "")
    _CURRENT.clear()
    try:
        return solve(task, os.getcwd())
    except BaseException as e:  # hand back whatever is in the working directory
        log(f"agent failed: {type(e).__name__}: {e}")
        ws = _CURRENT.get("ws")
        try:
            return ws.diff() if ws is not None else ""
        except Exception:
            return ""
