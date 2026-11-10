"""Command-line entry point: `sdd` / `specpilot` / `python -m specpilot`."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .audit import audit
from .gentests import gen_tests
from .installer import AGENTS, init, write_profile
from .pentest import NOT_RUN, SCAN_MODES, SEVERITIES, pentest
from .regression import regression
from .security import SecurityError, redact
from .spec import list_features, new_feature, phase_of, verify_feature


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sdd", description="SpecPilot: gated Spec-Driven Development for the AI SDLC.")
    p.add_argument("--version", action="version", version=f"specpilot {__version__}")
    p.add_argument("--dir", default=".", help="project root (default: current directory)")
    sub = p.add_subparsers(dest="command", metavar="<command>")

    s = sub.add_parser("init", help="profile the repo; install skills, commands, templates, test scaffolding")
    s.add_argument("--agent", choices=sorted(AGENTS), default="claude")
    s.add_argument("--force", action="store_true", help="overwrite installed skills/commands/templates")
    sub.add_parser("scan", help="refresh .sdd/codebase-profile.md")
    s = sub.add_parser("new", help="create .sdd/specs/<feature>/spec.md")
    s.add_argument("feature")
    sub.add_parser("status", help="phase and progress of every feature")
    s = sub.add_parser("verify", help="gate check: approvals, REQ -> task -> test traceability, secrets")
    s.add_argument("feature", nargs="?")
    s.add_argument("--strict", action="store_true")
    s = sub.add_parser("gen-tests", help="generate pytest-playwright tests from a spec's acceptance scenarios")
    s.add_argument("feature")
    s = sub.add_parser("regression", help="unit tests + e2e suite + all gates (CI entry point)")
    s.add_argument("--strict", action="store_true")
    s.add_argument("--pentest", action="append", metavar="TARGET", help="also run a Strix scan of TARGET")
    s.add_argument("--authorized", action="store_true")
    s = sub.add_parser("pentest", help="guarded Strix penetration test (key is read from your environment only)")
    s.add_argument("--target", action="append", metavar="PATH_OR_URL")
    s.add_argument("--authorized", action="store_true", help="confirm you may test every target")
    s.add_argument("--fail-on", choices=SEVERITIES)
    s.add_argument("--scan-mode", choices=SCAN_MODES)
    s.add_argument("--instruction")
    s.add_argument("--diff-base")
    s.add_argument("--max-budget", type=float, metavar="USD")
    sub.add_parser("audit", help="security self-check: committed secrets, .gitignore, config, CI")
    sub.add_parser("doctor", help="installation health")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    root = Path(args.dir).resolve()
    try:
        return _dispatch(args, root, parser)
    except SecurityError as exc:
        print(f"sdd: {redact(str(exc))}", file=sys.stderr)
        return 1


def _dispatch(args, root: Path, parser) -> int:
    cmd = args.command
    if cmd is None:
        parser.print_help()
        return 0
    if not root.is_dir():
        raise SecurityError(f"not a directory: {root}")

    if cmd == "init":
        result = init(root, args.agent, args.force)
        print("SpecPilot initialised:")
        for line in result["log"]:
            print(f"  + {line}")
        if result["profile"]["notes"]:
            print("\nObservations:")
            for note in result["profile"]["notes"]:
                print(f"  - {note}")
        print("\nNext steps:\n  1. Review .sdd/codebase-profile.md (fix anything marked CONFIRM)\n"
              "  2. In your agent: /sdd-constitution, then ratify .sdd/constitution.md yourself\n"
              "  3. Start a feature: /sdd-spec <idea>\n  4. Run: sdd audit")
        return 0

    if cmd == "scan":
        profile = write_profile(root)
        print("Profile updated:", ", ".join(l["name"] for l in profile["languages"]) or "no code detected")
        return 0

    if cmd == "new":
        d = new_feature(root, args.feature)
        print(f"Created {d.relative_to(root)}/spec.md. Next: /sdd-spec {args.feature}")
        return 0

    if cmd == "status":
        if not (root / ".sdd").is_dir():
            print("Not initialised. Run: sdd init")
            return 1
        features = list_features(root)
        if not features:
            print("No features yet. Start one: sdd new <feature-name>")
        for f in features:
            r = verify_feature(root, f)
            st = r["stats"]
            gates = f"{len(r['errors'])} gate issue(s)" if r["errors"] else "gates ok"
            print(f"{f:<28} {phase_of(st):<38} REQ {st.get('requirements', 0)}  "
                  f"tasks {st.get('tasksDone', 0)}/{st.get('tasks', 0)}  {gates}")
        return 0

    if cmd == "verify":
        targets = [args.feature] if args.feature else list_features(root)
        if not targets:
            print("No features to verify.")
            return 0
        bad = 0
        for f in targets:
            r = verify_feature(root, f, args.strict)
            st = r["stats"]
            print(f"\n{'FAIL' if r['errors'] else 'ok  '} {f}  (REQ {st.get('requirements', 0)}, tasks "
                  f"{st.get('tasksDone', 0)}/{st.get('tasks', 0)}, REQ with tests {st.get('reqsWithTests', 0)})")
            for e in r["errors"]:
                print(f"   ERROR  {e}")
            for w in r["warnings"]:
                print(f"   warn   {w}")
            bad += len(r["errors"])
        return 1 if bad else 0

    if cmd == "gen-tests":
        r = gen_tests(root, args.feature)
        print(f"{'Created' if r['created'] else 'Updated'} {r['file'].relative_to(root)}")
        if r["missing"]:
            print(f"No Given/When/Then scenario yet for: {', '.join(r['missing'])} (add them in spec.md section 6)")
        print("Run: pip install pytest-playwright && playwright install chromium && pytest tests/e2e")
        return 0

    if cmd == "regression":
        r = regression(root, args.strict, args.pentest, args.authorized)
        print("\nRegression summary:")
        for res in r["results"]:
            mark = "skip" if res["skipped"] else "ok  " if res["status"] == 0 else "FAIL"
            note = f"  ({res['note']})" if res.get("note") else ""
            print(f"  {mark} {res['label']}{note}")
        return 0 if r["ok"] else 1

    if cmd == "pentest":
        r = pentest(root, args.target or [], args.authorized, args.fail_on, args.scan_mode,
                    args.instruction, args.diff_base, args.max_budget)
        if not r["ran"]:
            print(f"PENTEST NOT RUN (exit {NOT_RUN}). This is not a pass.\n{r['reason']}")
        else:
            print({0: "Pentest clean at the chosen threshold.", 2: "Pentest found vulnerabilities."}
                  .get(r["status"], "Pentest ended with an error."), f"Record: {r['record']}")
        return r["status"]

    if cmd == "audit":
        r = audit(root)
        for level, message in r["findings"]:
            print(f"{level}  {message}")
        print("Security audit:", "passed" if r["ok"] else "FAILED",
              f"({len(r['findings'])} finding(s))" if r["findings"] else "(no findings)")
        return 0 if r["ok"] else 1

    if cmd == "doctor":
        checks = [(".sdd/config.json", (root / ".sdd/config.json").is_file()),
                  (".sdd/codebase-profile.md", (root / ".sdd/codebase-profile.md").is_file()),
                  (".sdd/constitution.md", (root / ".sdd/constitution.md").is_file()),
                  ("skills installed", any((root / d / "using-sdd/SKILL.md").is_file()
                                           for d in (".claude/skills", ".agents/skills"))),
                  ("e2e connector", (root / "tests/e2e/ui_connector.py").is_file())]
        for name, ok in checks:
            print(f"{'ok  ' if ok else 'MISSING'} {name}")
        cons = (root / ".sdd/constitution.md")
        if cons.is_file() and "Status: draft" in cons.read_text(encoding="utf-8", errors="replace"):
            print("note: constitution is still a draft; a human must ratify it")
        return 0 if all(ok for _, ok in checks) else 1

    parser.error(f"unknown command {cmd}")
    return 2
