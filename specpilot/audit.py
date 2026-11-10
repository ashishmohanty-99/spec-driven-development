"""`sdd audit`: security self-check of the SDD setup in this repository."""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from .installer import GITIGNORE_RULES
from .scan import walk
from .security import is_sensitive, read_text, scan_text_for_secrets
from .spec import load_config

SCAN_PREFIXES = (".sdd/", "tests/e2e/", ".claude/", ".agents/")
SCAN_FILES = ("CLAUDE.md", "AGENTS.md")


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


def audit(root: Path) -> dict:
    root = Path(root).resolve()
    findings: list[tuple[str, str]] = []  # (level, message); level is "FAIL" or "warn"
    files = walk(root)

    for rel in files:
        if rel in SCAN_FILES or rel.startswith(SCAN_PREFIXES):
            if rel.startswith(".sdd/security/"):
                continue
            for line_no, kind in scan_text_for_secrets(read_text(root / rel) or ""):
                findings.append(("FAIL", f"possible {kind} in {rel}:{line_no}. Remove it and rotate the credential."))

    tracked = _tracked(root)
    if tracked is not None:
        for rel in sorted(tracked):
            if is_sensitive(rel):
                findings.append(("FAIL", f"secret-like file is tracked by git: {rel}. Run: git rm --cached {rel}"))
            if rel.startswith("strix_runs/"):
                findings.append(("FAIL", "strix_runs/ is tracked by git; scan reports can expose vulnerabilities."))
                break

    ignore = {l.strip() for l in (read_text(root / ".gitignore") or "").splitlines()}
    missing = [r for r in GITIGNORE_RULES[:4] if r not in ignore]
    if missing:
        findings.append(("warn", f".gitignore is missing: {', '.join(missing)} (run: sdd init)"))

    raw_cfg = read_text(root / ".sdd" / "config.json") or ""
    if re.search(r"(?i)api[_-]?key|password|secret|token", raw_cfg):
        findings.append(("FAIL", ".sdd/config.json mentions a credential field. Config must never hold secrets."))
    cfg = load_config(root)
    for target in (cfg.get("pentest") or {}).get("allowedTargets") or []:
        if not re.match(r"^[a-z0-9.-]{1,253}$", str(target).lower()):
            findings.append(("warn", f'pentest.allowedTargets entry "{target}" should be a bare hostname'))

    ui_login = root / ".sdd" / "extensions" / "ui_login.py"
    text = read_text(ui_login) or ""
    if text and "os.environ" not in text:
        findings.append(("warn", ".sdd/extensions/ui_login.py does not read credentials from os.environ"))

    for wf in (f for f in files if f.startswith(".github/workflows/") and f.endswith((".yml", ".yaml"))):
        body = read_text(root / wf) or ""
        if "pull_request_target" in body and "LLM_API_KEY" in body:
            findings.append(("FAIL", f"{wf} exposes LLM_API_KEY to pull_request_target (fork PRs could steal it)."))
        if not re.search(r"^permissions:", body, flags=re.MULTILINE):
            findings.append(("warn", f"{wf} has no top-level `permissions:` block (default token is too broad)"))

    return {"findings": findings, "ok": not any(level == "FAIL" for level, _ in findings)}
