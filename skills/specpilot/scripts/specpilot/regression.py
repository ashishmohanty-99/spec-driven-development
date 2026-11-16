"""`sdd regression`: unit tests, generated e2e suite, every feature gate, optional pentest."""
from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

from .pentest import NOT_RUN, pentest
from .security import SecurityError, minimal_env, one_line, redact, safe_join
from .spec import e2e_dir, invalid_feature_dirs, list_features, load_config, verify_feature

E2E_ENV = ("SDD_BASE_URL", "SDD_UI_USER", "SDD_UI_PASS", "SDD_E2E_STRICT", "PLAYWRIGHT_BROWSERS_PATH",
           "DISPLAY", "PYTEST_ADDOPTS")


def _resolve(program: str, root: Path) -> str | None:
    """Find the executable. A path (./run.sh, scripts/test) is relative to the project, not the caller."""
    if Path(program).is_absolute():
        return program if Path(program).is_file() else None
    if "/" in program or "\\" in program:
        try:
            path = safe_join(root, program)
        except SecurityError:
            return None
        return str(path) if path.is_file() else None
    return shutil.which(program)


def _run(command: str, root: Path, extra_env: dict | None = None, passthrough: tuple = (),
         timeout: int = 3600) -> dict:
    """Run a configured command without a shell.

    A configured command that cannot start is a failure, never a skip: "nothing ran" must not pass.
    """
    label = one_line(command, 120)
    try:
        argv = shlex.split(command)
    except ValueError:
        argv = []
    if not argv:
        return {"label": label, "status": 1, "skipped": False, "note": "unparseable command"}
    exe = _resolve(argv[0], root)
    if not exe:
        return {"label": label, "status": 1, "skipped": False,
                "note": f"cannot run: {one_line(argv[0], 60)} not found"}
    env = minimal_env(E2E_ENV + tuple(passthrough))
    env.update(extra_env or {})
    try:
        proc = subprocess.run([exe, *argv[1:]], cwd=root, env=env, shell=False, timeout=timeout, check=False,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
    except subprocess.TimeoutExpired:
        return {"label": label, "status": 1, "skipped": False, "note": "timed out"}
    except OSError as exc:
        return {"label": label, "status": 1, "skipped": False, "note": f"cannot run: {exc.strerror or exc}"}
    print(redact(proc.stdout))
    return {"label": label, "status": proc.returncode, "skipped": False}


def regression(root: Path, strict: bool = False, pentest_targets: list[str] | None = None,
               authorized: bool = False) -> dict:
    root = Path(root).resolve()
    cfg = load_config(root)
    commands = cfg["commands"]
    results = []
    # Extra variable *names* the project's tests need (e.g. DATABASE_URL). Values stay in the shell.
    passthrough = tuple(n for n in cfg["envPassthrough"] if n.replace("_", "").isalnum())

    if commands.get("test"):
        results.append(_run(commands["test"], root, passthrough=passthrough))
    else:
        results.append({"label": "unit tests", "status": 0, "skipped": True,
                        "note": 'set "commands.test" in .sdd/config.json'})

    e2e = e2e_dir(root)
    if e2e.is_dir() and any(e2e.glob("test_*.py")):
        command = commands.get("e2e") or f"pytest {shlex.quote(cfg['e2eDir'])}"
        r = _run(command, root, {"SDD_E2E_STRICT": "1"} if strict else None, passthrough)
        if r["status"] == 5:  # pytest: no tests collected
            r.update(status=0, skipped=True, note="no e2e tests collected")
        results.append(r)
    else:
        results.append({"label": "e2e suite", "status": 0, "skipped": True,
                        "note": "no generated tests yet (run: sdd gen-tests <feature>)"})

    features = list_features(root)
    invalid = invalid_feature_dirs(root)
    gate_errors = sum(len(verify_feature(root, f, strict)["errors"]) for f in features) + len(invalid)
    results.append({"label": f"sdd verify ({len(features)} feature(s))", "status": 1 if gate_errors else 0,
                    "skipped": not features and not invalid,
                    "note": f"{gate_errors} gate error(s)" if gate_errors else None})

    if pentest_targets:
        p = pentest(root, pentest_targets, authorized=authorized)
        # A requested scan that did not run fails the sweep: skipped is not the same as clean.
        note = one_line(p["reason"], 160) if p.get("reason") else {2: "findings", 1: "scan error"}.get(p["status"])
        results.append({"label": "sdd pentest", "status": p["status"], "skipped": False,
                        "note": "not run: " + note if p["status"] == NOT_RUN and note else note})

    return {"results": results, "ok": all(r["status"] == 0 for r in results)}
