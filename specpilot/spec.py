"""Spec, task and scenario parsing, and the mechanical gates behind `sdd verify`."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .scan import TEST_FILE, walk
from .security import SecurityError, read_text, safe_join, scan_text_for_secrets, validate_feature, write_text

ASSETS = Path(__file__).parent / "assets"
REQ_ID = r"REQ-[A-Z0-9]+(?:-\d+)?"
# A definition is `- REQ-001: text` (optionally bold). `REQ-001 - Given...` lines are scenarios.
REQ_DEF = re.compile(rf"^\s*(?:[-*]|\d+\.)\s+\**({REQ_ID})(?:\*\*)?:\s*(.*)$")
REQ_REF = re.compile(rf"\b{REQ_ID}\b")
TASK_LINE = re.compile(r"^\s*[-*]\s+\[([ xX])\]\s+\**(T-\d+)\**[\s:.)-]+(.*)$")
SCENARIO = re.compile(rf"^\s*[-*]\s+\**({REQ_ID})\**\s+[—–-]\s+(.+)$")
GWT = re.compile(r"^Given\s+(.+?),\s*when\s+(.+?),\s*then\s+(.+)$", re.IGNORECASE)
PLACEHOLDER = re.compile(r"…|<[^>]+>|\bTBD\b|\.\.\.")
DEFAULT_CONFIG = {
    "version": 1, "specsDir": ".sdd/specs", "e2eDir": "tests/e2e", "strict": False,
    "requireTestsPerRequirement": True,
    "commands": {"test": None, "e2e": "pytest tests/e2e"},
    "pentest": {"allowedTargets": [], "failOn": "high", "scanMode": "quick"},
}


def load_config(root: Path) -> dict:
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    text = read_text(Path(root) / ".sdd" / "config.json")
    if text:
        try:
            user = json.loads(text)
        except ValueError:
            user = {}
        if isinstance(user, dict):
            for key, value in user.items():
                if isinstance(value, dict) and isinstance(cfg.get(key), dict):
                    cfg[key].update(value)
                else:
                    cfg[key] = value
    return cfg


def specs_dir(root: Path) -> Path:
    return safe_join(root, str(load_config(root).get("specsDir") or ".sdd/specs"))


def feature_dir(root: Path, feature: str) -> Path:
    return safe_join(specs_dir(root), validate_feature(feature))


def list_features(root: Path) -> list[str]:
    d = specs_dir(root)
    if not d.is_dir():
        return []
    return sorted(e.name for e in d.iterdir() if e.is_dir() and not e.is_symlink()
                  and re.match(r"^[a-z0-9][a-z0-9-]{0,63}$", e.name))


def new_feature(root: Path, feature: str) -> Path:
    d = feature_dir(root, feature)
    if d.exists():
        raise SecurityError(f'feature "{feature}" already exists')
    template = read_text(Path(root) / ".sdd" / "templates" / "spec.md") or \
        (ASSETS / "templates" / "spec.md").read_text(encoding="utf-8")
    write_text(root, d / "spec.md", template.replace("{{FEATURE}}", feature))
    return d


def _strip(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def parse_spec(text: str) -> dict:
    clean = _strip(text)
    reqs, placeholders, titles = [], [], {}
    for line in clean.splitlines():
        m = REQ_DEF.match(line)
        if m:
            reqs.append(m.group(1))
            titles.setdefault(m.group(1), m.group(2).strip())
            if PLACEHOLDER.search(line):
                placeholders.append(m.group(1))
    status = re.search(r"^\s*(?:\*\*)?Status(?:\*\*)?\s*:\s*(?:\*\*)?\s*(\w+)", clean, flags=re.IGNORECASE | re.MULTILINE)
    return {
        "reqs": reqs, "titles": titles, "placeholders": placeholders,
        "open": re.findall(r"\[NEEDS CLARIFICATION[^\]]*\]", clean),
        "status": status.group(1).lower() if status else "draft",
        "approved": bool(status and status.group(1).lower() in ("approved", "shipped")),
    }


def parse_tasks(text: str) -> list[dict]:
    tasks = []
    for line in _strip(text).splitlines():
        m = TASK_LINE.match(line)
        if m:
            tasks.append({"id": m.group(2), "done": m.group(1).lower() == "x",
                          "covers": REQ_REF.findall(m.group(3)), "text": m.group(3).strip()})
    return tasks


def parse_scenarios(text: str) -> list[dict]:
    out = []
    for line in _strip(text).splitlines():
        m = SCENARIO.match(line)
        if not m:
            continue
        body = m.group(2).strip()
        g = GWT.match(body)
        out.append({"req": m.group(1), "raw": body,
                    "given": g.group(1).strip() if g else None,
                    "when": g.group(2).strip() if g else None,
                    "then": g.group(3).strip() if g else None})
    return out


def test_refs(root: Path) -> dict:
    """Map requirement id -> test files that mention it."""
    refs: dict = {}
    for rel in walk(root):
        if rel.startswith(".sdd/") or not TEST_FILE.search(rel):
            continue
        text = read_text(Path(root) / rel)
        if not text:
            continue
        for rid in set(REQ_REF.findall(text)):
            refs.setdefault(rid, []).append(rel)
    return refs


def verify_feature(root: Path, feature: str, strict: bool = False) -> dict:
    """Run every mechanical gate for one feature. Returns {errors, warnings, stats}."""
    errors: list[str] = []
    warnings: list[str] = []
    try:
        d = feature_dir(root, feature)
    except SecurityError as exc:
        return {"errors": [str(exc)], "warnings": [], "stats": {}}
    spec_text = read_text(d / "spec.md")
    if spec_text is None:
        return {"errors": [f'spec.md missing for "{feature}"'], "warnings": [], "stats": {}}
    cfg = load_config(root)
    strict = bool(strict or cfg.get("strict"))
    spec = parse_spec(spec_text)
    plan_text = read_text(d / "plan.md")
    tasks_text = read_text(d / "tasks.md")
    tasks = parse_tasks(tasks_text) if tasks_text else []
    downstream = bool(plan_text or tasks_text)

    if not spec["reqs"]:
        errors.append('spec.md defines no requirements (expected "- REQ-001: When ..., the system shall ...")')
    for dup in sorted({r for r in spec["reqs"] if spec["reqs"].count(r) > 1}):
        errors.append(f"duplicate requirement id {dup}")
    if spec["placeholders"]:
        (errors if spec["approved"] or downstream else warnings).append(
            f"placeholder text left in {', '.join(spec['placeholders'])}")
    if spec["open"]:
        (errors if spec["approved"] or downstream else warnings).append(
            f"{len(spec['open'])} unresolved [NEEDS CLARIFICATION] marker(s) in spec.md")
    if downstream and not spec["approved"]:
        errors.append('plan/tasks exist but spec.md is not "Status: approved" (gate skipped)')
    if tasks_text and not plan_text:
        errors.append("tasks.md exists without plan.md (gate skipped)")

    known, covered = set(spec["reqs"]), set()
    for t in tasks:
        if not t["covers"]:
            errors.append(f"{t['id']} references no requirement (add \"covers: REQ-...\")")
        for r in t["covers"]:
            if r in known:
                covered.add(r)
            else:
                errors.append(f"{t['id']} references unknown {r}")
    if tasks_text:
        for r in spec["reqs"]:
            if r not in covered:
                errors.append(f"{r} is not covered by any task")

    refs = test_refs(root)
    done = {r for t in tasks if t["done"] for r in t["covers"]}
    if cfg.get("requireTestsPerRequirement", True):
        for r in spec["reqs"]:
            if r in done and r not in refs:
                (errors if strict else warnings).append(
                    f"{r} has completed task(s) but no test file names it")

    # Security gate: credentials must never be committed inside SDD artifacts.
    for name, text in (("spec.md", spec_text), ("plan.md", plan_text), ("tasks.md", tasks_text),
                       ("verification.md", read_text(d / "verification.md"))):
        for line_no, kind in scan_text_for_secrets(text or ""):
            errors.append(f"SECURITY: possible {kind} in {name}:{line_no} (remove it and rotate the credential)")

    stats = {"requirements": len(spec["reqs"]), "tasks": len(tasks),
             "tasksDone": sum(1 for t in tasks if t["done"]),
             "reqsWithTests": sum(1 for r in spec["reqs"] if r in refs),
             "status": spec["status"], "approved": spec["approved"],
             "hasPlan": bool(plan_text), "hasTasks": bool(tasks_text)}
    return {"errors": errors, "warnings": warnings, "stats": stats}


def phase_of(stats: dict) -> str:
    if not stats:
        return "SPECIFY"
    if stats.get("status") == "shipped":
        return "SHIPPED"
    if not stats["approved"]:
        return "SPECIFY / CLARIFY (awaiting approval)"
    if not stats["hasPlan"]:
        return "PLAN"
    if not stats["hasTasks"]:
        return "TASKS"
    if stats["tasks"] and stats["tasksDone"] < stats["tasks"]:
        return "BUILD"
    return "VERIFY / SHIP"
