"""`sdd audit`: security self-check of the SDD setup in this repository."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from .installer import GITIGNORE_RULES, vendored_cli_is_ours
from .scan import walk
from .security import SECRET_PATTERNS, is_sensitive, one_line, read_text, scan_text_for_secrets
from .spec import DEFAULT_CONFIG, load_config

SCAN_DIRS = (".sdd", ".claude", ".agents")
SCAN_FILES = ("CLAUDE.md", "AGENTS.md")
CREDENTIAL_KEY = re.compile(r"(?i)api[_-]?key|passw(or)?d|secret|token|credential")


def _tracked(root: Path) -> set | None:
    git = shutil.which("git")
    if not git:
        return None
    try:
        # core.fsmonitor is disabled so a hostile repository config cannot run a program here.
        out = subprocess.run([git, "-c", "core.fsmonitor=false", "ls-files", "-z"], cwd=root, shell=False,
                             capture_output=True, text=True, timeout=30, check=False)
        return set(filter(None, out.stdout.split("\0"))) if out.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def _config_findings(root: Path) -> list[tuple[str, str]]:
    """Config must never hold a secret: flag unknown credential-like keys and secret-shaped values."""
    text = read_text(root / ".sdd" / "config.json")
    if text is None:
        return []
    try:
        data = json.loads(text)
    except ValueError:
        return [("FAIL", ".sdd/config.json is not valid JSON; every command refuses to run with it.")]
    found = []

    def visit(node, path):
        if isinstance(node, dict):
            for key, value in node.items():
                here = f"{path}.{key}" if path else str(key)
                known = key in DEFAULT_CONFIG or (path in DEFAULT_CONFIG and isinstance(DEFAULT_CONFIG[path], dict)
                                                  and key in DEFAULT_CONFIG[path]) or here == "agent"
                if not known and CREDENTIAL_KEY.search(str(key)):
                    message = (f'.sdd/config.json has a credential-like field "{one_line(here, 60)}". '
                               "Config must never hold secrets.")
                    found.append(("FAIL", message))
                visit(value, here)
        elif isinstance(node, list):
            for item in node:
                visit(item, path)
        elif isinstance(node, str) and any(p.search(node) for _label, p in SECRET_PATTERNS):
            found.append(("FAIL", f'.sdd/config.json value under "{one_line(path, 60)}" looks like a credential.'))

    visit(data, "")
    return found


def audit(root: Path) -> dict:
    root = Path(root).resolve()
    findings: list[tuple[str, str]] = []  # (level, message); level is "FAIL" or "warn"
    e2e = load_config(root)["e2eDir"]

    # Walk each area directly so a very large repository cannot push these files past the walk cap.
    scan = [f for f in SCAN_FILES if (root / f).is_file()]
    for area in (*SCAN_DIRS, e2e):
        scan += walk(root, area)
    vendored_ok = vendored_cli_is_ours(root)
    for rel in dict.fromkeys(scan):
        if is_sensitive(rel):
            continue  # never opened; reported below if tracked
        if rel.startswith(".sdd/bin/") and vendored_ok:
            continue  # byte-identical to this package
        for line_no, kind in scan_text_for_secrets(read_text(root / rel) or ""):
            findings.append(("FAIL", f"possible {kind} in {rel}:{line_no}. Remove it and rotate the credential."))
    if (root / ".sdd" / "bin").exists() and not vendored_ok:
        findings.append(("warn", ".sdd/bin does not match this SpecPilot version. Review it, then run: sdd init --vendor"))

    tracked = _tracked(root)
    if tracked is not None:
        for rel in sorted(tracked):
            if is_sensitive(rel):
                findings.append(("FAIL", f"secret-like file is tracked by git: {rel}. Run: git rm --cached {rel}"))
        if any(rel.startswith("strix_runs/") for rel in tracked):
            findings.append(("FAIL", "strix_runs/ is tracked by git; scan reports can expose vulnerabilities."))

    ignore = {line.strip() for line in (read_text(root / ".gitignore") or "").splitlines()}
    missing = [r for r in GITIGNORE_RULES[:4] if r not in ignore]
    if missing:
        findings.append(("warn", f".gitignore is missing: {', '.join(missing)} (run: sdd init)"))

    findings += _config_findings(root)
    for target in load_config(root)["pentest"].get("allowedTargets") or []:
        if not re.fullmatch(r"[a-z0-9.-]{1,253}", target.lower()):
            findings.append(("warn", f'pentest.allowedTargets entry "{one_line(target, 60)}" should be a bare hostname'))

    text = read_text(root / ".sdd" / "extensions" / "ui_login.py") or ""
    if text and "os.environ" not in text:
        findings.append(("warn", ".sdd/extensions/ui_login.py does not read credentials from os.environ"))

    for wf in walk(root, ".github/workflows"):
        if not wf.endswith((".yml", ".yaml")):
            continue
        body = read_text(root / wf) or ""
        if "pull_request_target" in body and "LLM_API_KEY" in body:
            findings.append(("FAIL", f"{wf} exposes LLM_API_KEY to pull_request_target (fork PRs could steal it)."))
        if not re.search(r"^permissions:", body, flags=re.MULTILINE):
            findings.append(("warn", f"{wf} has no top-level `permissions:` block (default token is too broad)"))

    return {"findings": findings, "ok": not any(level == "FAIL" for level, _ in findings)}
