"""Offline smoke test: run agent_main against a scripted fake proxy in a temp working directory."""

import importlib
import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

AGENT_DIR = Path(__file__).resolve().parents[1]


def tool_call(i, name, **args):
    return {"id": f"call_{i}", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


class FakeProxy(BaseHTTPRequestHandler):
    script: list = []
    requests: list = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeProxy.requests.append({"auth": self.headers.get("Authorization"), "body": body})
        if not FakeProxy.script:
            self.send_response(429)
            self.end_headers()
            return
        message = FakeProxy.script.pop(0)
        out = json.dumps({"choices": [{"message": message}], "usage": {"cost": 0.01}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *args):
        pass


@pytest.fixture
def agent(monkeypatch, tmp_path):
    server = HTTPServer(("127.0.0.1", 0), FakeProxy)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv("SANDBOX_PROXY_URL", f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_TIMEOUT", "300")
    for var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    monkeypatch.syspath_prepend(str(AGENT_DIR))
    sys.modules.pop("agent", None)
    module = importlib.import_module("agent")
    work = tmp_path / "work"
    work.mkdir()
    (work / "calc.py").write_text("def add(a, b):\n    return a - b\n")
    (work / ".gitignore").write_text("out/\n")
    monkeypatch.chdir(work)
    FakeProxy.requests = []
    yield module, work
    server.shutdown()


def test_edits_new_files_and_ignored_paths_end_up_in_patch(agent):
    module, work = agent
    FakeProxy.script = [
        {"content": "", "tool_calls": [tool_call(1, "read_file", path="calc.py")]},
        {"content": "", "tool_calls": [tool_call(2, "replace_in_file", path="calc.py", old_text="a - b", new_text="a + b")]},
        {"content": "", "tool_calls": [tool_call(3, "write_file", path="out/answer.txt", content="42\n")]},
        {"content": "", "tool_calls": [tool_call(4, "bash", command="python3 -c 'import calc; print(calc.add(2, 3))'")]},
        {"content": "", "tool_calls": [tool_call(5, "finish", summary="fixed add, wrote answer")]},
    ]
    patch = module.agent_main({"problem_statement": "Fix add() and write 42 to out/answer.txt"})

    assert "-    return a - b" in patch and "+    return a + b" in patch
    assert "out/answer.txt" in patch and "+42" in patch
    assert FakeProxy.requests[0]["auth"] == "Bearer test-key"
    tool_results = [m for m in FakeProxy.requests[-1]["body"]["messages"] if m["role"] == "tool"]
    assert "exit code 0\n5" in tool_results[-1]["content"]

    # The patch applies cleanly to an untouched copy.
    clean = work.parent / "clean"
    clean.mkdir()
    (clean / "calc.py").write_text("def add(a, b):\n    return a - b\n")
    (clean / ".gitignore").write_text("out/\n")
    subprocess.run(["git", "init", "-q"], cwd=clean, check=True)
    subprocess.run(["git", "apply", "-"], cwd=clean, input=patch, text=True, check=True)
    assert (clean / "out" / "answer.txt").read_text() == "42\n"
    assert not (work / ".git").exists()  # the agent never creates or touches a repo .git


def test_budget_exhaustion_still_returns_work_done(agent):
    module, _ = agent
    FakeProxy.script = [
        {"content": "", "tool_calls": [tool_call(1, "write_file", path="notes.md", content="partial\n")]},
    ]  # the next request gets 429
    patch = module.agent_main({"problem_statement": "Write notes"})
    assert "notes.md" in patch and "+partial" in patch


def test_paths_outside_workdir_are_refused(agent):
    module, _ = agent
    FakeProxy.script = [
        {"content": "", "tool_calls": [tool_call(1, "write_file", path="../escape.txt", content="x")]},
        {"content": "", "tool_calls": [tool_call(2, "finish", summary="done")]},
    ]
    module.agent_main({"problem_statement": "noop"})
    tool_msgs = [m for m in FakeProxy.requests[-1]["body"]["messages"] if m["role"] == "tool"]
    assert "outside the working directory" in tool_msgs[0]["content"]
