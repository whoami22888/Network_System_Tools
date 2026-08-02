#!/usr/bin/env python3
"""Local consent-gated security assistant bridge for the PWA.

This server intentionally runs only on localhost by default. It connects to a local
Ollama WhiteRabbitNeo model, exposes a small chat API, records user-visible logs,
and only executes allow-listed terminal commands after explicit consent.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
TOOLS_DIR = ROOT / "tools"
BUILTIN_TOOLS_DIR = TOOLS_DIR / "builtin"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "whiterabbitneo"
ALLOWLIST = {"pwd", "whoami", "date", "uname", "ip", "ifconfig", "netstat", "ss", "nslookup", "dig", "traceroute", "curl"}

STATE = {"internet_enabled": False, "logging_enabled": True}


def now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def append_log(kind: str, payload: dict[str, Any]) -> Path | None:
    if not STATE["logging_enabled"]:
        return None
    LOG_DIR.mkdir(exist_ok=True)
    path = LOG_DIR / f"findings-{dt.datetime.now(dt.UTC).date().isoformat()}.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"time": now(), "kind": kind, "payload": payload}, sort_keys=True) + "\n")
    return path


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.end_headers()
    handler.wfile.write(body)


class AgentHandler(BaseHTTPRequestHandler):
    server_version = "NetworkSystemToolsAgent/0.1"

    def do_OPTIONS(self) -> None:  # noqa: N802
        json_response(self, 200, {"ok": True})

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            json_response(self, 200, {"ok": True, "model": self.server.model, "state": STATE})
            return
        if self.path == "/logs":
            LOG_DIR.mkdir(exist_ok=True)
            files = sorted(path.name for path in LOG_DIR.glob("*.jsonl"))
            json_response(self, 200, {"files": files})
            return
        if self.path == "/tools":
            json_response(self, 200, {"tools": load_tools()})
            return
        json_response(self, 404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            json_response(self, 400, {"error": "invalid json"})
            return

        if self.path == "/settings":
            STATE["internet_enabled"] = bool(payload.get("internet_enabled", STATE["internet_enabled"]))
            STATE["logging_enabled"] = bool(payload.get("logging_enabled", STATE["logging_enabled"]))
            append_log("settings", STATE.copy())
            json_response(self, 200, {"ok": True, "state": STATE})
            return

        if self.path == "/chat":
            prompt = str(payload.get("message", "")).strip()
            if not prompt:
                json_response(self, 400, {"error": "message required"})
                return
            system = (
                "You are WhiteRabbitNeo running as a defensive security assistant. "
                "Ask for human consent before terminal or internet actions. "
                "Explain every action in plain language and keep recommendations lawful and authorized."
            )
            answer = self.call_ollama(system, prompt)
            append_log("chat", {"prompt": prompt, "answer": answer})
            json_response(self, 200, {"answer": answer, "model": self.server.model})
            return

        if self.path == "/terminal":
            command = str(payload.get("command", "")).strip()
            consent = bool(payload.get("consent"))
            if not consent:
                json_response(self, 403, {"error": "human consent required"})
                return
            result = run_allowlisted_command(command, STATE["internet_enabled"])
            append_log("terminal", {"command": command, "result": result})
            json_response(self, 200 if result["ok"] else 400, result)
            return

        if self.path == "/tools":
            name = safe_tool_name(str(payload.get("name", "tool.json")))
            content = payload.get("content", {})
            TOOLS_DIR.mkdir(exist_ok=True)
            destination = TOOLS_DIR / name
            destination.write_text(json.dumps(content, indent=2, sort_keys=True), encoding="utf-8")
            append_log("tool_upload", {"name": name})
            json_response(self, 200, {"ok": True, "path": str(destination.relative_to(ROOT))})
            return

        json_response(self, 404, {"error": "not found"})

    def call_ollama(self, system: str, prompt: str) -> str:
        data = json.dumps({"model": self.server.model, "prompt": f"{system}\n\nUser: {prompt}", "stream": False}).encode("utf-8")
        request = urllib.request.Request(f"{self.server.ollama_url}/api/generate", data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body = json.loads(response.read())
                return str(body.get("response", ""))
        except (urllib.error.URLError, TimeoutError) as exc:
            return f"Ollama is unavailable at {self.server.ollama_url}. Start it with `ollama run {self.server.model}`. Error: {exc}"


def run_allowlisted_command(command: str, internet_enabled: bool) -> dict[str, Any]:
    parts = command.split()
    if not parts:
        return {"ok": False, "error": "empty command"}
    executable = Path(parts[0]).name
    if executable not in ALLOWLIST:
        return {"ok": False, "error": f"command not allowed: {executable}", "allowlist": sorted(ALLOWLIST)}
    if executable in {"curl", "dig", "nslookup", "traceroute"} and not internet_enabled:
        return {"ok": False, "error": "internet activity is disabled by the user toggle"}
    try:
        completed = subprocess.run(parts, cwd=ROOT, text=True, capture_output=True, timeout=20, check=False)
        return {"ok": completed.returncode == 0, "returncode": completed.returncode, "stdout": completed.stdout[-8000:], "stderr": completed.stderr[-8000:]}
    except Exception as exc:  # defensive boundary for subprocess failures
        return {"ok": False, "error": str(exc)}


def safe_tool_name(name: str) -> str:
    cleaned = "".join(char for char in name if char.isalnum() or char in {"-", "_", "."}).strip(".")
    return cleaned or "tool.json"


def load_tools() -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for directory in (BUILTIN_TOOLS_DIR, TOOLS_DIR):
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = {"name": path.stem, "error": "invalid json"}
            payload["source"] = str(path.relative_to(ROOT))
            tools.append(payload)
    return tools


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Network System Tools AI bridge")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=int(os.environ.get("NST_AGENT_PORT", "8787")), type=int)
    parser.add_argument("--ollama-url", default=os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL))
    parser.add_argument("--model", default=os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL))
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), AgentHandler)
    server.ollama_url = args.ollama_url
    server.model = args.model
    print(f"agent listening on http://{args.host}:{args.port} using {args.model} at {args.ollama_url}")
    server.serve_forever()


if __name__ == "__main__":
    main()
