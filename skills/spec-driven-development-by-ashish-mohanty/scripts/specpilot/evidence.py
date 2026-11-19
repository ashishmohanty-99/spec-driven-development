"""Red-first proof: show that a feature's acceptance tests failed before the code and pass after it.

    sdd prove red <feature>     run the feature's acceptance tests; they must FAIL; record it
    sdd prove green <feature>   run them again; they must PASS, and the test file must be unchanged

A test that has never been seen failing proves nothing, and a test that was edited between red and
green may have been edited to pass. The record (.sdd/specs/<feature>/evidence.json) holds the test
file's hash at each step, so `sdd verify` can check both properties without trusting anyone's word.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import shlex
import shutil
import subprocess
from pathlib import Path

from .gentests import RENDER, default_command, framework
from .security import SecurityError, minimal_env, one_line, read_text, redact, safe_join, write_text
from .spec import e2e_dir, feature_dir, load_config

E2E_ENV = ("SDD_BASE_URL", "SDD_UI_USER", "SDD_UI_PASS", "PLAYWRIGHT_BROWSERS_PATH", "DISPLAY", "PYTEST_ADDOPTS")


def test_file(root: Path, feature: str) -> Path:
    name = RENDER[framework(root)][1].format(feature=feature, snake=feature.replace("-", "_"))
    return e2e_dir(root) / name


def file_hash(path: Path) -> str | None:
    text = read_text(path)
    return hashlib.sha256(text.encode("utf-8")).hexdigest() if text is not None else None


def load(root: Path, feature: str) -> dict:
    try:
        data = json.loads(read_text(feature_dir(root, feature) / "evidence.json") or "{}")
    except ValueError:
        data = {}
    return data if isinstance(data, dict) else {}


def _command(root: Path, feature: str) -> list[str]:
    cfg = load_config(root)
    fw = framework(root)
    path = test_file(root, feature)
    rel = str(path.relative_to(Path(root).resolve()))
    custom = cfg["commands"].get("e2e")
    if fw == "gherkin" or custom:
        if not custom:
            raise SecurityError('set "commands.e2e" in .sdd/config.json to the command that runs your feature files')
        return [*shlex.split(custom), rel]
    return shlex.split(default_command(fw, shlex.quote(rel)))


def prove(root: Path, feature: str, phase: str, timeout: int = 1800) -> dict:
    """Run the feature's acceptance tests and record the outcome if it is the expected one."""
    root = Path(root).resolve()
    if phase not in ("red", "green"):
        raise SecurityError("phase must be red or green")
    path = test_file(root, feature)
    digest = file_hash(path)
    if digest is None:
        raise SecurityError(f"no acceptance tests for {feature} yet (run: sdd gen-tests {feature})")
    record = load(root, feature)
    if phase == "green":
        red = record.get("red")
        if not red:
            raise SecurityError(f"no red run recorded for {feature}. Run `sdd prove red {feature}` before the code is written.")
        if red["testHash"] != digest:
            raise SecurityError("the acceptance tests changed since the red run, so a pass now proves nothing. "
                                f"Record a new red run first: sdd prove red {feature}")
    argv = _command(root, feature)
    program = argv[0]
    exe = str(safe_join(root, program)) if ("/" in program and not Path(program).is_absolute()) else \
        (program if Path(program).is_absolute() else shutil.which(program))
    if not exe or not Path(exe).is_file():
        raise SecurityError(f"cannot run the acceptance tests: {one_line(program, 60)} not found")
    cfg = load_config(root)
    env = minimal_env(E2E_ENV + tuple(n for n in cfg["envPassthrough"] if n.replace("_", "").isalnum()))
    env["SDD_E2E_STRICT"] = "1"  # a gap is a failure in both phases, so green means every scenario ran
    if cfg.get("baseUrl") and "SDD_BASE_URL" not in env:
        env["SDD_BASE_URL"] = cfg["baseUrl"]
    try:
        proc = subprocess.run([exe, *argv[1:]], cwd=root, env=env, shell=False, timeout=timeout, check=False,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
    except subprocess.TimeoutExpired as exc:
        raise SecurityError("the acceptance tests timed out") from exc
    output = redact(proc.stdout)
    passed = proc.returncode == 0
    ok = passed if phase == "green" else not passed
    result = {"phase": phase, "ok": ok, "exit": proc.returncode, "output": output.strip().splitlines()[-15:]}
    if ok:
        record[phase] = {"at": _dt.datetime.now(_dt.UTC).isoformat(timespec="seconds"), "testHash": digest,
                         "exit": proc.returncode, "command": one_line(" ".join(argv), 200)}
        if phase == "red":
            record.pop("green", None)  # a new red run invalidates an older green
        write_text(root, feature_dir(root, feature) / "evidence.json", json.dumps(record, indent=2) + "\n")
    return result


def status(root: Path, feature: str) -> dict:
    """What the record proves right now: {tests, red, green, problem}."""
    path = test_file(root, feature)
    digest = file_hash(path)
    record = load(root, feature)
    red, green = record.get("red"), record.get("green")
    problem = None
    if digest is None:
        problem = None  # no generated tests: nothing to prove yet
    elif not red:
        problem = "no red run recorded (the tests were never shown to fail)"
    elif not green:
        problem = "no green run recorded"
    elif green["testHash"] != digest or red["testHash"] != green["testHash"]:
        problem = "the acceptance tests changed after they were proven; record red and green again"
    return {"tests": digest is not None, "red": bool(red), "green": bool(green), "problem": problem}
