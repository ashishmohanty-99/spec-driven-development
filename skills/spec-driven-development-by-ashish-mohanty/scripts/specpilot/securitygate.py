"""`sdd security`: one gate over four layers, each reported as clean, findings, error or NOT RUN.

  secrets       whole repository + git history (TruffleHog or gitleaks if installed, else built-in)
  code-scan     static analysis of the source with the analyser that fits the stack
  dependencies  third-party packages against known-vulnerability databases
  pentest       Strix against a target, when one is given

SpecPilot does not reimplement analysers. It finds the ones that fit the detected stack, runs those
that are installed, and never lets "not installed" read as "nothing found".

Exit codes: 0 clean; 2 findings; 1 a tool failed; 3 strict mode and an enabled layer did not run.
"""
from __future__ import annotations

import datetime as _dt
import json
import shutil
import subprocess
from pathlib import Path

from .pentest import NOT_RUN, pentest
from .secretscan import scan_secrets, worktree_files
from .security import is_sensitive, minimal_env, one_line, read_text, redact, write_text
from .spec import enabled, load_config

CLEAN, FINDINGS, ERROR, NOT_RUN_S, OFF = "clean", "findings", "error", "NOT RUN", "off"

# id, layer, languages it applies to (None = any), argv, exit codes that mean "findings", marker file needed
TOOLS = [
    ("semgrep", "code-scan", None, ["semgrep", "scan", "--config", "auto", "--error", "--quiet", "--metrics", "off"], {1}, None),
    ("bandit", "code-scan", {"Python"}, ["bandit", "-r", ".", "-q", "-ll", "-x", "./.sdd,./tests,./node_modules,./.venv,./venv"], {1}, None),
    ("gosec", "code-scan", {"Go"}, ["gosec", "-quiet", "./..."], {1}, None),
    ("brakeman", "code-scan", {"Ruby"}, ["brakeman", "-q", "--no-pager"], {3}, None),
    ("osv-scanner", "dependencies", None, ["osv-scanner", "scan", "-r", "."], {1}, None),
    ("trivy", "dependencies", None, ["trivy", "fs", "--exit-code", "2", "--severity", "HIGH,CRITICAL", "--quiet", "."], {2}, None),
    ("pip-audit", "dependencies", {"Python"}, ["pip-audit", "-r", "requirements.txt"], {1}, "requirements.txt"),
    ("npm", "dependencies", {"JavaScript", "TypeScript"}, ["npm", "audit", "--audit-level=high"], {1}, "package-lock.json"),
    ("cargo-audit", "dependencies", {"Rust"}, ["cargo", "audit"], {1}, "Cargo.lock"),
    ("govulncheck", "dependencies", {"Go"}, ["govulncheck", "./..."], {3}, "go.mod"),
    ("bundle-audit", "dependencies", {"Ruby"}, ["bundle-audit", "check"], {1}, "Gemfile.lock"),
]
EXECUTABLE = {"cargo-audit": "cargo-audit"}  # program to look for when it differs from argv[0]
HINTS = {"code-scan": "install an analyser for your stack, for example semgrep (any language), bandit (Python), "
                      "gosec (Go) or brakeman (Ruby)",
         "dependencies": "install a dependency auditor, for example osv-scanner or trivy (any language), pip-audit, "
                         "npm audit, cargo-audit, govulncheck or bundle-audit"}


def _languages(root: Path) -> set:
    try:
        profile = json.loads(read_text(Path(root) / ".sdd" / "codebase-profile.json") or "{}")
    except ValueError:
        profile = {}
    return {entry.get("name") for entry in profile.get("languages", []) if isinstance(entry, dict)}


def applicable(root: Path, layer: str) -> list[tuple]:
    langs = _languages(root)
    return [t for t in TOOLS if t[1] == layer and (t[2] is None or t[2] & langs)
            and (t[5] is None or (Path(root) / t[5]).is_file())]


def _run_tool(tool: tuple, root: Path, timeout: int) -> dict | None:
    name, _layer, _langs, argv, finding_codes, _marker = tool
    exe = shutil.which(argv[0])
    if not exe or (name in EXECUTABLE and not shutil.which(EXECUTABLE[name])):
        return None
    try:
        proc = subprocess.run([exe, *argv[1:]], cwd=root, shell=False, capture_output=True, text=True,
                              errors="replace", timeout=timeout, check=False, env=minimal_env())
    except subprocess.TimeoutExpired:
        return {"tool": name, "status": ERROR, "detail": "timed out"}
    except OSError as exc:
        return {"tool": name, "status": ERROR, "detail": f"could not start: {exc.strerror or exc}"}
    status = CLEAN if proc.returncode == 0 else FINDINGS if proc.returncode in finding_codes else ERROR
    tail = [redact(line) for line in (proc.stdout + proc.stderr).strip().splitlines()[-25:]]
    return {"tool": name, "status": status, "detail": f"exit {proc.returncode}", "output": tail}


def _layer(root: Path, layer: str, timeout: int) -> dict:
    candidates = applicable(root, layer)
    runs = [r for r in (_run_tool(t, root, timeout) for t in candidates) if r is not None]
    if not runs:
        return {"layer": layer, "status": NOT_RUN_S, "tools": [],
                "detail": f"no tool installed ({HINTS[layer]})"}
    status = ERROR if any(r["status"] == ERROR for r in runs) else \
        FINDINGS if any(r["status"] == FINDINGS for r in runs) else CLEAN
    return {"layer": layer, "status": status, "tools": runs,
            "detail": ", ".join(f"{r['tool']}: {r['status']}" for r in runs)}


def _tracked_secret_files(root: Path) -> list[str]:
    return [f for f in worktree_files(root) if is_sensitive(f) and (Path(root) / ".git").exists()
            and _is_tracked(root, f)]


def _is_tracked(root: Path, rel: str) -> bool:
    git = shutil.which("git")
    if not git:
        return False
    try:
        out = subprocess.run([git, "-c", "core.fsmonitor=false", "ls-files", "--error-unmatch", "--", rel], cwd=root,
                             shell=False, capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return out.returncode == 0


def security_gate(root: Path, strict: bool = False, history: bool | None = None, verify_live: bool = False,
                  pentest_targets: list[str] | None = None, authorized: bool = False, timeout: int = 1800) -> dict:
    root = Path(root).resolve()
    cfg = load_config(root)
    sec = cfg["security"]
    layers = []

    if enabled(cfg, "secrets"):
        result = scan_secrets(root, history=sec.get("history", True) if history is None else history,
                              verify_live=verify_live, exclude=tuple(sec.get("exclude", [])),
                              engine=sec.get("engine", "auto"))
        findings = list(result["findings"])
        for rel in _tracked_secret_files(root):
            findings.append({"kind": "secret-like file tracked by git", "file": rel, "line": 0,
                             "fingerprint": "-", "where": "working tree"})
        status = result["status"] if result["status"] == ERROR else (FINDINGS if findings else CLEAN)
        accepted = f", {result['accepted']} accepted" if result["accepted"] else ""
        layers.append({"layer": "secrets", "status": status, "engine": result["engine"], "findings": findings,
                       "notes": result["notes"],
                       "detail": f"{result['engine']} engine, {len(findings)} finding(s){accepted}"})
    else:
        layers.append({"layer": "secrets", "status": OFF, "detail": "switched off by the team"})

    for layer in ("code-scan", "dependencies"):
        layers.append(_layer(root, layer, timeout) if enabled(cfg, layer)
                      else {"layer": layer, "status": OFF, "detail": "switched off by the team"})

    if pentest_targets:
        p = pentest(root, pentest_targets, authorized=authorized)
        status = {0: CLEAN, 2: FINDINGS, NOT_RUN: NOT_RUN_S}.get(p["status"], ERROR)
        layers.append({"layer": "pentest", "status": status, "detail": one_line(p.get("reason") or status, 200)})
    elif enabled(cfg, "pentest"):
        layers.append({"layer": "pentest", "status": NOT_RUN_S,
                       "detail": "no target given (a person runs: sdd pentest --target . --authorized)",
                       "optional": True})  # needs a person and a model; never required by --strict
    else:
        layers.append({"layer": "pentest", "status": OFF, "detail": "switched off by the team"})

    statuses = [entry["status"] for entry in layers]
    missing = [entry["layer"] for entry in layers if entry["status"] == NOT_RUN_S and not entry.get("optional")]
    code = 2 if FINDINGS in statuses else 1 if ERROR in statuses else NOT_RUN if (strict and missing) else 0
    gate = {"layers": layers, "exit": code, "notRun": missing, "strict": strict}
    if (root / ".sdd").is_dir():
        record = {"at": _dt.datetime.now(_dt.UTC).isoformat(timespec="seconds"), "exit": code,
                  "layers": [{"layer": e["layer"], "status": e["status"], "detail": e["detail"]} for e in layers]}
        write_text(root, root / ".sdd" / "security" / "latest-gate.json", json.dumps(record, indent=2) + "\n")
    return gate
