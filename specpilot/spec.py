"""Spec, task and scenario parsing, and the mechanical gates behind `sdd verify`."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .scan import TEST_FILE, walk
from .security import (
    FEATURE_RE,
    SecurityError,
    is_sensitive,
    one_line,
    read_text,
    safe_join,
    scan_text_for_secrets,
    validate_feature,
    write_text,
)

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
    "commands": {"test": None, "e2e": None},  # e2e None means: pytest <e2eDir>
    "envPassthrough": [],
    "pentest": {"allowedTargets": [], "failOn": "high", "scanMode": "quick"},
}


def _str_list(value, key: str) -> list:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise SecurityError(f'.sdd/config.json: "{key}" must be a list of strings')
    return value


def load_config(root: Path) -> dict:
    """Read .sdd/config.json. A config that exists but cannot be trusted is an error, never ignored:
    silently falling back to defaults would switch off settings such as "strict"."""
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    path = Path(root) / ".sdd" / "config.json"
    if not path.exists() and not path.is_symlink():
        return cfg
    text = read_text(path)
    if text is None:
        raise SecurityError(".sdd/config.json is unreadable (symlink, too large, or not a regular file)")
    try:
        user = json.loads(text)
    except ValueError as exc:
        raise SecurityError(f".sdd/config.json is not valid JSON: {exc}") from exc
    if not isinstance(user, dict):
        raise SecurityError(".sdd/config.json must contain a JSON object")
    for key, value in user.items():
        if isinstance(cfg.get(key), dict):
            if not isinstance(value, dict):
                raise SecurityError(f'.sdd/config.json: "{key}" must be an object')
            cfg[key].update(value)
        else:
            cfg[key] = value
    for key in ("specsDir", "e2eDir"):
        if not isinstance(cfg[key], str) or not cfg[key].strip():
            raise SecurityError(f'.sdd/config.json: "{key}" must be a non-empty string')
    for name, command in cfg["commands"].items():
        if command is not None and not isinstance(command, str):
            raise SecurityError(f'.sdd/config.json: "commands.{name}" must be a string or null')
    _str_list(cfg["envPassthrough"], "envPassthrough")
    _str_list(cfg["pentest"].get("allowedTargets", []), "pentest.allowedTargets")
    return cfg


def e2e_dir(root: Path) -> Path:
    return safe_join(root, load_config(root)["e2eDir"])


def specs_dir(root: Path) -> Path:
    return safe_join(root, str(load_config(root).get("specsDir") or ".sdd/specs"))


def feature_dir(root: Path, feature: str) -> Path:
    return safe_join(specs_dir(root), validate_feature(feature))


def _feature_entries(root: Path) -> list[Path]:
    d = specs_dir(root)
    if d.exists() and not d.is_dir():
        raise SecurityError(f"{d.name} exists but is not a directory")
    return sorted(e for e in d.iterdir() if e.is_dir()) if d.is_dir() else []


def list_features(root: Path) -> list[str]:
    return [e.name for e in _feature_entries(root) if not e.is_symlink() and FEATURE_RE.match(e.name)]


def invalid_feature_dirs(root: Path) -> list[str]:
    """Directories under the specs folder that the gates cannot address. They are errors, not ignored."""
    return [one_line(e.name, 60) for e in _feature_entries(root) if e.is_symlink() or not FEATURE_RE.match(e.name)]


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
            if PLACEHOLDER.search(line) or not m.group(2).strip():
                placeholders.append(m.group(1))
    # The status word must stand alone on its line: "approved-pending-review" is not approved.
    status = re.search(
        r"^[ \t]*(?:\*\*)?Status(?:\*\*)?[ \t]*:[ \t]*(?:\*\*)?[ \t]*(\w+)[ \t]*(?:\*\*)?[ \t]*\r?$",
        clean, flags=re.IGNORECASE | re.MULTILINE)
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


# A generated test for a requirement that has no scenario yet. It names the id but proves nothing.
STUB = re.compile(rf"@pytest\.mark\.requirement\('{REQ_ID}'\)\ndef \w+\(page\):\n    # {REQ_ID}\n    missing\(.*\n")


def _test_files(root: Path) -> list[str]:
    found = dict.fromkeys(walk(root))
    for sub in ("tests", "test", load_config(root)["e2eDir"]):  # not subject to the global file cap
        found.update(dict.fromkeys(walk(root, sub)))
    return [f for f in found if TEST_FILE.search(f) and not f.startswith(".sdd/") and not is_sensitive(f)]


def test_refs(root: Path) -> dict:
    """Map requirement id -> test files that mention it (generated placeholder stubs do not count)."""
    refs: dict = {}
    for rel in _test_files(root):
        text = read_text(Path(root) / rel)
        if not text:
            continue
        for rid in set(REQ_REF.findall(STUB.sub("", text))):
            refs.setdefault(rid, []).append(rel)
    return refs


def _id_owners(root: Path) -> dict:
    """Requirement id -> features that define it. Ids repeat across features (each starts at REQ-001)."""
    owners: dict = {}
    for f in list_features(root):
        text = read_text(feature_dir(root, f) / "spec.md")
        for rid in set(parse_spec(text)["reqs"]) if text else ():
            owners.setdefault(rid, set()).add(f)
    return owners


def feature_refs(root: Path, feature: str, refs: dict | None = None, owners: dict | None = None) -> dict:
    """Test references that count for this feature.

    An id defined by one feature only is matched anywhere. An id shared by several features counts
    only in a test file whose path names the feature (tests/e2e/test_<feature>.py, tests/<feature>/...).
    """
    refs = test_refs(root) if refs is None else refs
    owners = _id_owners(root) if owners is None else owners
    keys = {feature, feature.replace("-", "_")}
    out = {}
    for rid, files in refs.items():
        if len(owners.get(rid, ())) > 1:
            files = [f for f in files if any(k in f for k in keys)]
        if files:
            out[rid] = files
    return out


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

    refs = feature_refs(root, feature)
    done = {r for t in tasks if t["done"] for r in t["covers"]}
    if cfg.get("requireTestsPerRequirement", True):
        for r in spec["reqs"]:
            if r in done and r not in refs:
                (errors if strict else warnings).append(
                    f"{r} has completed task(s) but no test file names it")

    if spec["status"] == "shipped":  # shipped means finished: every task done, every requirement proven
        if not tasks:
            errors.append("spec is shipped but has no tasks")
        for t in tasks:
            if not t["done"]:
                errors.append(f"spec is shipped but {t['id']} is not checked")
        for r in spec["reqs"]:
            if r not in refs:
                errors.append(f"spec is shipped but no test names {r}")

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
