"""Command-line entry point: `sdd` / `specpilot` / `python -m specpilot`."""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

from . import __version__
from .audit import audit
from .gentests import framework, gen_tests
from .installer import AGENTS, init, write_profile
from .onboarding import answer, questions
from .pentest import NOT_RUN, SCAN_MODES, SEVERITIES, pentest
from .regression import regression
from .security import SecurityError, one_line, redact
from .spec import (
    LIFECYCLE,
    e2e_dir,
    enabled,
    invalid_feature_dirs,
    list_features,
    load_config,
    new_feature,
    next_step,
    save_config,
    skipped_checks,
    verify_feature,
)


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sdd", description="Spec-Driven Development for the AI SDLC. Not sure what to do? Run: sdd next")
    p.add_argument("--version", action="version", version=f"sdd {__version__}")
    p.add_argument("--dir", default=".", help="project root (default: current directory)")
    common = argparse.ArgumentParser(add_help=False)  # lets --dir also follow the command
    common.add_argument("--dir", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    _sub = p.add_subparsers(dest="command", metavar="<command>")

    class sub:
        @staticmethod
        def add_parser(name, **kwargs):
            return _sub.add_parser(name, parents=[common], **kwargs)

    s = sub.add_parser("init", help="understand the repo; install skills, commands, templates, test scaffolding")
    s.add_argument("--agent", choices=sorted(AGENTS), default="claude")
    s.add_argument("--force", action="store_true", help="refresh installed skills/commands/templates")
    s.add_argument("--vendor", action="store_true",
                   help="also copy the CLI into .sdd/bin so the project needs no installation")
    sub.add_parser("next", help="the single next action for every feature (start here)")
    s = sub.add_parser("questions", help="setup questions the tool could not answer by itself")
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("answer", help="answer a setup question: sdd answer <id> <value>")
    s.add_argument("id")
    s.add_argument("value")
    s = sub.add_parser("lifecycle", help="show the checks, or switch one off/on with its consequence")
    s.add_argument("action", nargs="?", choices=("show", "skip", "enable"), default="show")
    s.add_argument("check", nargs="?")
    s.add_argument("--reason", help="why the team is skipping this check (required for skip)")
    sub.add_parser("scan", help="refresh .sdd/codebase-profile.md")
    s = sub.add_parser("new", help="create .sdd/specs/<feature>/spec.md")
    s.add_argument("feature")
    sub.add_parser("status", help="phase and progress of every feature")
    s = sub.add_parser("verify", help="gate check: approvals, REQ -> task -> test traceability, secrets")
    s.add_argument("feature", nargs="?")
    s.add_argument("--strict", action="store_true")
    s = sub.add_parser("gen-tests", help="generate acceptance tests from a spec's scenarios, in your stack's form")
    s.add_argument("feature")
    s = sub.add_parser("regression", help="unit tests + acceptance tests + all gates (CI entry point)")
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
        return NOT_RUN if args.command == "pentest" else 1
    except (OSError, ValueError, TypeError, AttributeError) as exc:  # bad input must not print a traceback
        print(f"sdd: {type(exc).__name__}: {redact(str(exc))}", file=sys.stderr)
        return NOT_RUN if args.command == "pentest" else 1


def _skipped_banner(cfg: dict) -> None:
    """Every report says which checks the team switched off, so a quiet gate is never mistaken for a pass."""
    off = skipped_checks(cfg)
    if not off:
        return
    print("\nSwitched off by the team (not checked):")
    for name in off:
        title, _what, cost = LIFECYCLE[name]
        reason = (cfg["skipped"].get(name) or {}).get("reason")
        print(f"  ! {title} [{name}]: {cost}" + (f"  Reason given: {one_line(reason, 120)}" if reason else ""))


def _print_questions(root: Path) -> int:
    open_qs = questions(root)
    if not open_qs:
        print("Setup is complete: nothing left to ask.")
        return 0
    print(f"{len(open_qs)} setup question(s). Each has a safe default; answer with: sdd answer <id> <value>\n")
    for q in open_qs:
        print(f"[{q['id']}] {q['question']}")
        print(f"    Why: {q['why']}")
        if q["kind"] == "checks":
            for opt in q["options"]:
                print(f"      - {opt['label']} [{opt['value']}]  if skipped: {opt['skipping_means']}")
            print('    Keep everything: sdd answer lifecycle all   |   Switch one off: sdd lifecycle skip <check> --reason "..."')
        else:
            for opt in q["options"]:
                value, label = (opt["value"], opt["label"]) if isinstance(opt, dict) else (opt, opt)
                mark = "  (recommended)" if value == q["recommended"] else ""
                print(f"      - {value}" + (f": {label}" if label != value else "") + mark)
            if q["recommended"] and not q["options"]:
                print(f"    Recommended: {q['recommended']}")
        print()
    return 0


def _lifecycle(args, root: Path) -> int:
    cfg = load_config(root)
    if args.action == "show":
        print("Lifecycle checks. Writing an approved spec before code is always on.\n")
        for name, (title, what, cost) in LIFECYCLE.items():
            state = "ON " if enabled(cfg, name) else "OFF"
            print(f"  [{state}] {title} [{name}]\n         {what}\n         If skipped: {cost}")
        print('\nSwitch one off:  sdd lifecycle skip <check> --reason "why"\nSwitch it on:    sdd lifecycle enable <check>')
        return 0
    if args.check not in LIFECYCLE:
        raise SecurityError(f"choose a check: {', '.join(LIFECYCLE)}")
    title, _what, cost = LIFECYCLE[args.check]
    if args.action == "skip":
        reason = one_line(args.reason or "", 200)
        if len(reason) < 5:
            raise SecurityError('skipping a check needs a reason a teammate can read later: --reason "..."')
        cfg["lifecycle"][args.check] = False
        cfg["skipped"][args.check] = {"reason": reason, "date": _dt.datetime.now(_dt.UTC).date().isoformat()}
        save_config(root, cfg)
        print(f"WARNING: '{title}' is now OFF for this repository.\n  What this means: {cost}\n"
              f"  Reason recorded: {reason}\n  Every status and verify report will say this check is off.\n"
              f"  Turn it back on any time: sdd lifecycle enable {args.check}")
        return 0
    cfg["lifecycle"][args.check] = True
    cfg["skipped"].pop(args.check, None)
    save_config(root, cfg)
    print(f"'{title}' is ON again.")
    return 0


def _next(root: Path) -> int:
    if not (root / ".sdd").is_dir():
        print("This repository is not set up yet.\n  Next: sdd init --vendor   (or ask your agent: \"Set up spec-driven development here\")")
        return 0
    cfg = load_config(root)
    open_qs = questions(root)
    cons = root / ".sdd" / "constitution.md"
    steps = []
    if open_qs:
        steps.append(f"Answer {len(open_qs)} setup question(s): sdd questions")
    if cfg["project"].get("kind") == "greenfield" and not list_features(root):
        steps.append("Empty repository: create the project structure with /sdd-scaffold (you approve the layout)")
    if enabled(cfg, "constitution") and cons.is_file() and "Status: draft" in (cons.read_text(encoding="utf-8", errors="replace")):
        steps.append("Agree the team rules: /sdd-constitution, then a person sets `Status: ratified`")
    features = list_features(root)
    if steps:
        print("Setup:")
        for s in steps:
            print(f"  -> {s}")
    if not features:
        print('\nNo features yet.\n  -> Start one: /sdd-spec "<what you want to build>"')
    else:
        print("\nFeatures:")
        for f in features:
            r = verify_feature(root, f)
            phase, action = next_step(r["stats"], f)
            print(f"  {f}  [{phase}]")
            if r["errors"]:
                print(f"     ! {len(r['errors'])} gate issue(s): sdd verify {f}")
            print(f"     -> {action}")
    _skipped_banner(cfg)
    return 0


def _dispatch(args, root: Path, parser) -> int:
    cmd = args.command
    if cmd is None:
        parser.print_help()
        return 0
    if not root.is_dir():
        raise SecurityError(f"not a directory: {root}")

    if cmd == "init":
        result = init(root, args.agent, args.force, args.vendor)
        profile = result["profile"]
        print("Spec-Driven Development is set up in this repository.\n")
        langs = ", ".join(f"{entry['name']}" for entry in profile["languages"][:4]) or "no code yet (new project)"
        print("What I found:")
        print(f"  Languages:   {langs}")
        for label, key in (("Frameworks", "frameworks"), ("Test tools", "testTools"), ("CI", "ci")):
            if profile[key]:
                print(f"  {label + ':':<12} {', '.join(profile[key][:6])}")
        print(f"  Acceptance tests will be generated as: {framework(root)}")
        print("\nWhat I did:")
        for line in result["log"]:
            print(f"  + {line}")
        notes = [n for n in profile["notes"] if not n.startswith("No agent instruction file")]  # just created
        if notes:
            print("\nWorth knowing:")
            for note in notes:
                print(f"  - {note}")
        open_qs = questions(root)
        print(f"\nNext: {'sdd questions  (' + str(len(open_qs)) + ' quick setup question(s)), then ' if open_qs else ''}sdd next")
        return 0

    if cmd == "next":
        return _next(root)
    if cmd == "questions":
        if args.json:
            print(json.dumps(questions(root), indent=2))
            return 0
        return _print_questions(root)
    if cmd == "answer":
        print(answer(root, args.id, args.value))
        left = questions(root)
        print(f"{len(left)} question(s) left: sdd questions" if left else "Setup is complete. Next: sdd next")
        return 0
    if cmd == "lifecycle":
        return _lifecycle(args, root)

    if cmd == "scan":
        profile = write_profile(root)
        print("Profile updated:", ", ".join(entry["name"] for entry in profile["languages"]) or "no code detected")
        return 0

    if cmd == "new":
        d = new_feature(root, args.feature)
        print(f"Created {d.relative_to(root)}/spec.md. Next: /sdd-spec {args.feature}")
        return 0

    if cmd == "status":
        if not (root / ".sdd").is_dir():
            print("Not set up yet. Run: sdd init --vendor")
            return 1
        cfg = load_config(root)
        features = list_features(root)
        if not features:
            print('No features yet. Start one: /sdd-spec "<idea>"')
        for name in invalid_feature_dirs(root):
            print(f"{name:<28} INVALID NAME: rename to kebab-case so the gates can check it")
        for f in features:
            r = verify_feature(root, f)
            st = r["stats"]
            gates = f"{len(r['errors'])} gate issue(s)" if r["errors"] else "gates ok"
            print(f"{f:<28} {next_step(st, f)[0]:<38} REQ {st.get('requirements', 0)}  "
                  f"tasks {st.get('tasksDone', 0)}/{st.get('tasks', 0)}  {gates}")
        _skipped_banner(cfg)
        return 0

    if cmd == "verify":
        cfg = load_config(root)
        targets = [args.feature] if args.feature else list_features(root)
        bad = 0
        if not args.feature:
            for name in invalid_feature_dirs(root):
                print(f"\nFAIL {name}\n   ERROR  feature directory name is not kebab-case, so it cannot be checked")
                bad += 1
        if not targets and not bad:
            print("No features to verify.")
            return 0
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
        _skipped_banner(cfg)
        return 1 if bad else 0

    if cmd == "gen-tests":
        r = gen_tests(root, args.feature)
        print(f"{'Created' if r['created'] else 'Updated'} {r['file'].relative_to(root)}  ({r['framework']})")
        if r["missing"]:
            print(f"No Given/When/Then scenario yet for: {', '.join(r['missing'])} (add them in spec.md section 6)")
        hint = {"playwright-python": "pip install pytest-playwright && playwright install chromium",
                "playwright-ts": "npm i -D @playwright/test && npx playwright install chromium",
                "gherkin": f"write step definitions in your language (see {r['e2eDir']}/README.md) and set commands.e2e"}
        print(f"First time: {hint[r['framework']]}")
        if r["command"]:
            print(f"Run them: {r['command']}")
        return 0

    if cmd == "regression":
        r = regression(root, args.strict, args.pentest, args.authorized)
        print("\nRegression summary:")
        for res in r["results"]:
            mark = "skip" if res["skipped"] else "ok  " if res["status"] == 0 else "FAIL"
            note = f"  ({res['note']})" if res.get("note") else ""
            print(f"  {mark} {res['label']}{note}")
        _skipped_banner(load_config(root))
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
        cfg = load_config(root)
        checks = [(".sdd/config.json", (root / ".sdd/config.json").is_file()),
                  (".sdd/codebase-profile.md", (root / ".sdd/codebase-profile.md").is_file()),
                  ("skills installed", any((root / d / "using-sdd/SKILL.md").is_file()
                                           for d in (".claude/skills", ".agents/skills")))]
        if enabled(cfg, "constitution"):
            checks.append((".sdd/constitution.md", (root / ".sdd/constitution.md").is_file()))
        if enabled(cfg, "e2e"):
            checks.append(("acceptance-test folder", e2e_dir(root).is_dir()))
        for name, ok in checks:
            print(f"{'ok  ' if ok else 'MISSING'} {name}")
        cons = (root / ".sdd/constitution.md")
        if enabled(cfg, "constitution") and cons.is_file() and \
                "Status: draft" in cons.read_text(encoding="utf-8", errors="replace"):
            print("note: team rules are still a draft; a person must ratify them")
        _skipped_banner(cfg)
        return 0 if all(ok for _, ok in checks) else 1

    parser.error(f"unknown command {cmd}")
    return 2
