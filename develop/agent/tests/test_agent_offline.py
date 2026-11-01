"""Offline tests: run the agent against a scripted fake proxy in temporary working directories."""

import importlib
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

AGENT_DIR = Path(__file__).resolve().parents[1]


def call(i, name, **args):
    return {"id": f"c{i}", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


def turn(*calls, content=""):
    return {"content": content, "tool_calls": list(calls)}


CHECKLIST = dict(deliverables=["calc.py with add() fixed"], requirements=["add(2, 3) == 5"],
                 assumptions=["python3 is present"], interpretation="plain integer addition")


class FakeProxy(BaseHTTPRequestHandler):
    script: list = []
    requests: list = []
    cost = 0.001

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeProxy.requests.append({"auth": self.headers.get("Authorization"), "body": body})
        if not FakeProxy.script:
            self._send(429, {"detail": "Evaluation run cost budget exceeded"})
            return
        message = FakeProxy.script.pop(0)
        self._send(200, {"choices": [{"message": message}], "usage": {"cost": FakeProxy.cost, "prompt_tokens": 1000}})

    def _send(self, code, obj):
        out = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *args):
        pass


def tool_results(i=-1):
    return [m for m in FakeProxy.requests[i]["body"]["messages"] if m["role"] == "tool"]


@pytest.fixture
def env(monkeypatch, tmp_path):
    server = HTTPServer(("127.0.0.1", 0), FakeProxy)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv("SANDBOX_PROXY_URL", f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_TIMEOUT", "600")
    monkeypatch.setenv("RIDGES_MAX_COST_USD", "0.29")
    for var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    monkeypatch.syspath_prepend(str(AGENT_DIR))
    sys.modules.pop("agent", None)
    agent = importlib.import_module("agent")
    work = tmp_path / "work"
    work.mkdir()
    (work / "calc.py").write_text("def add(a, b):\n    return a - b\n")
    (work / ".gitignore").write_text("out/\nlocal.cfg\n")
    monkeypatch.chdir(work)
    FakeProxy.requests, FakeProxy.cost = [], 0.001
    yield agent, work
    server.shutdown()


def clean_copy(work: Path, patch: str) -> Path:
    clean = work.parent / "clean"
    clean.mkdir()
    (clean / "calc.py").write_text("def add(a, b):\n    return a - b\n")
    (clean / ".gitignore").write_text("out/\nlocal.cfg\n")
    subprocess.run(["git", "init", "-q"], cwd=clean, check=True)
    subprocess.run(["git", "apply", "-"], cwd=clean, input=patch, text=True, check=True)
    return clean


def happy_path_script():
    return [
        turn(call(1, "read_file", path="calc.py"), call(2, "write_file", path="calc.py", content="x")),
        turn(call(3, "record_checklist", **CHECKLIST)),
        turn(call(4, "edit_file", path="calc.py", old_text="a - b", new_text="a + b"),
             call(5, "write_file", path="out/answer.txt", content="5\n")),
        turn(call(6, "finish", result_files=["calc.py", "out/answer.txt"], summary="fixed", verified=True)),
        turn(call(7, "bash", command="python3 -c 'import calc; print(calc.add(2, 3))'")),
        turn(call(8, "finish", result_files=["calc.py", "out/answer.txt"], summary="fixed", verified=True,
                  evidence=["python3 -c ... printed 5"])),
    ]


def test_happy_path_checklist_gate_and_clean_patch(env):
    agent, work = env
    FakeProxy.script = happy_path_script()
    patch = agent.agent_main({"problem_statement": "Fix add() in `calc.py` and write the answer to out/answer.txt"})

    assert "+    return a + b" in patch and "out/answer.txt" in patch
    assert FakeProxy.requests[0]["auth"] == "Bearer test-key"
    opening = FakeProxy.requests[0]["body"]["messages"][1]["content"]
    assert "calc.py: file exists" in opening and "out/answer.txt: not found" in opening
    first = tool_results(1)
    assert "record your understanding with record_checklist" in first[-1]["content"]
    assert "budget left" in first[-1]["content"]
    gate = [m["content"] for m in tool_results(4) if "Before this is final" in m["content"]]
    assert gate and "add(2, 3) == 5" in gate[0]
    assert len(FakeProxy.requests) == 6  # verified: no second attempt
    clean = clean_copy(work, patch)
    assert (clean / "out" / "answer.txt").read_text() == "5\n"
    assert not (work / ".git").exists()


def test_second_finish_needs_a_fresh_command(env):
    agent, _ = env
    s = happy_path_script()
    FakeProxy.script = s[:4] + [s[5]] + s[4:]
    agent.agent_main({"problem_statement": "Fix add()"})
    msgs = [m["content"] for m in tool_results()]
    assert any("Run the checks first" in m for m in msgs)
    assert len(FakeProxy.requests) == 7  # accepted on the finish after the fresh command; no second attempt


def test_symlinks_pycache_and_nested_repos_are_left_out(env):
    agent, work = env
    nested = work / "vendor"
    nested.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=nested, check=True)
    FakeProxy.script = [
        turn(call(1, "record_checklist", **CHECKLIST)),
        turn(call(2, "bash", command="ln -s calc.py link.py && mkdir -p __pycache__ && echo x > __pycache__/a.pyc "
                                    "&& echo v > vendor/v.txt && sed -i 's/a - b/a + b/' calc.py")),
        turn(call(3, "finish", result_files=["calc.py"], summary="s", verified=True)),
        turn(call(4, "bash", command="true")),
        turn(call(5, "finish", result_files=["calc.py"], summary="s", verified=True)),
    ]
    patch = agent.agent_main({"problem_statement": "Fix add()"})
    assert "a + b" in patch
    assert "link.py" not in patch and "__pycache__" not in patch and "vendor" not in patch
    opening = FakeProxy.requests[0]["body"]["messages"][1]["content"]
    assert "separate git repositories" in opening and "vendor" in opening
    clean_copy(work, patch)


def test_budget_exhaustion_still_returns_the_work(env):
    agent, _ = env
    FakeProxy.script = [
        turn(call(1, "record_checklist", **CHECKLIST)),
        turn(call(2, "write_file", path="notes.md", content="partial\n")),
    ]  # the next request gets the proxy's budget 429
    patch = agent.agent_main({"problem_statement": "Write notes"})
    assert "notes.md" in patch and "+partial" in patch
    assert len(FakeProxy.requests) == 3  # no second attempt once the proxy reports the budget is gone


def test_unverified_first_attempt_triggers_a_second_and_it_wins(env):
    agent, work = env
    (work / "local.cfg").write_text("original\n")  # git-ignored, pre-existing
    FakeProxy.script = [
        # attempt A: wrong fix, reports it could not verify
        turn(call(1, "record_checklist", **CHECKLIST)),
        turn(call(2, "edit_file", path="calc.py", old_text="a - b", new_text="a * b"),
             call(3, "write_file", path="local.cfg", content="changed by A\n")),
        turn(call(4, "finish", result_files=["calc.py"], summary="unsure", verified=False)),
        turn(call(5, "bash", command="python3 -c 'import calc; print(calc.add(2, 3))'")),
        turn(call(6, "finish", result_files=["calc.py"], summary="prints 6, not 5", verified=False)),
        # attempt B starts from the original files
        turn(call(7, "bash", command="cat calc.py local.cfg")),
        turn(call(8, "record_checklist", **CHECKLIST)),
        turn(call(9, "edit_file", path="calc.py", old_text="a - b", new_text="a + b")),
        turn(call(10, "finish", result_files=["calc.py"], summary="fixed", verified=True)),
        turn(call(11, "bash", command="python3 -c 'import calc; print(calc.add(2, 3))'")),
        turn(call(12, "finish", result_files=["calc.py"], summary="fixed", verified=True, evidence=["printed 5"])),
    ]
    patch = agent.agent_main({"problem_statement": "Fix add()"})
    assert "+    return a + b" in patch and "a * b" not in patch
    b_opening = FakeProxy.requests[5]["body"]["messages"][1]["content"]
    assert "colleague" in b_opening and "prints 6, not 5" in b_opening
    restored = tool_results(6)[-1]["content"]
    assert "return a - b" in restored and "original" in restored


def test_pairwise_judge_decides_between_two_unverified_attempts(env):
    agent, _ = env
    unverified = lambda base, new: [  # noqa: E731
        turn(call(base, "record_checklist", **CHECKLIST)),
        turn(call(base + 1, "edit_file", path="calc.py", old_text="a - b", new_text=new)),
        turn(call(base + 2, "finish", result_files=["calc.py"], summary=new, verified=False)),
        turn(call(base + 3, "bash", command="true")),
        turn(call(base + 4, "finish", result_files=["calc.py"], summary=new, verified=False)),
    ]
    FakeProxy.script = (unverified(1, "a * b") + unverified(10, "a + b")
                        + [{"content": "B is right. VERDICT: SECOND"}, {"content": "VERDICT: FIRST"}])
    patch = agent.agent_main({"problem_statement": "Fix add()"})
    assert "a + b" in patch
    judge_requests = [r for r in FakeProxy.requests if "tools" not in r["body"]]
    assert len(judge_requests) == 2


def test_repeated_identical_calls_are_refused(env):
    agent, _ = env
    FakeProxy.script = [turn(call(i, "bash", command="ls")) for i in range(8)]
    agent.agent_main({"problem_statement": "noop"})
    contents = [m["content"] for m in tool_results(8)]
    assert "repeated this exact call" in contents[4]
    assert contents[7].startswith("error: this exact call has been repeated")


def test_paths_outside_the_working_directory_are_refused_as_results(env):
    agent, _ = env
    FakeProxy.script = [
        turn(call(1, "record_checklist", **CHECKLIST)),
        turn(call(2, "finish", result_files=["../escape.txt"], summary="s", verified=True)),
    ]
    agent.agent_main({"problem_statement": "noop"})
    assert "outside the working directory" in tool_results(2)[-1]["content"]


def test_meter_tiers_and_guard():
    sys.modules.pop("agent", None)
    sys.path.insert(0, str(AGENT_DIR))
    agent = importlib.import_module("agent")
    m = agent.Meter(0.29, 1200)
    assert m.tier() == "high" and m.can_call()
    m.spent = m.cap * 0.8
    assert m.tier() == "low"
    m.last_cost = 0.02
    assert not m.can_call() and m.can_call(use_reserve=True)
    m.spent = m.cap
    assert m.tier() == "critical" and not m.can_call(use_reserve=True)
