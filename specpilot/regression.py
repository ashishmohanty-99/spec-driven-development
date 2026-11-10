"""`sdd regression`: unit tests, generated e2e suite, every feature gate, optional pentest."""
from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

from .pentest import NOT_RUN, pentest
from .security import minimal_env, one_line, redact
from .spec import list_features, load_config, safe_join, verify_feature

E2E_ENV = ("SDD_BASE_URL", "SDD_UI_USER", "SDD_UI_PASS", "SDD_E2E_STRICT", "PLAYWRIGHT_BROWSERS_PATH",
           "DISPLAY", "PYTEST_ADDOPTS")


def _run(command: str, root: Path, extra_env: dict | None = None, passthrough: tuple = (),
         timeout: int = 3600) -> dict:
    """Run a configured command without a shell. The command comes from .sdd/config.json."""
    label = one_line(command, 120)
    try:
        argv = shlex.split(command)
    except ValueError:
        return {"label": label, "status": 1, "skipped": False, "note": "unparseable command"}
    exe = shutil.which(argv[0]) if argv else None
    if not exe:
        return {"label": label, "status": 0, "skipped": True, "note": f"{argv[0] if argv else '?'} not installed"}
    env = minimal_env(E2E_ENV + tuple(passthrough))
    env.update(extra_env or {})
    try:
        proc = subprocess.run([exe, *argv[1:]], cwd=root, env=env, shell=False, timeout=timeout, check=False,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
        print(redact(proc.stdout))
        return {"label": label, "status": proc.returncode, "skipped": False}
    except subprocess.TimeoutExpired:
        return {"label": label, "status": 1, "skipped": False, "note": "timed out"}


def regression(root: Path, strict: bool = False, pentest_targets: list[str] | None = None,
               authorized: bool = False) -> dict:
    root = Path(root).resolve()
    cfg = load_config(root)
    commands = cfg.get("commands") or {}
    results = []
    # Extra variable *names* the project's tests need (e.g. DATABASE_URL). Values stay in the shell.
    passthrough = tuple(n for n in (cfg.get("envPassthrough") or [])
                        if isinstance(n, str) and n.replace("_", "").isalnum())

    if commands.get("test"):
        results.append(_run(str(commands["test"]), root, passthrough=passthrough))
    else:
        results.append({"label": "unit tests", "status": 0, "skipped": True,
                        "note": 'set "commands.test" in .sdd/config.json'})

    e2e_dir = safe_join(root, str(cfg.get("e2eDir") or "tests/e2e"))
    has_e2e = e2e_dir.is_dir() and any(e2e_dir.glob("test_*.py"))
    if has_e2e and commands.get("e2e"):
        r = _run(str(commands["e2e"]), root, {"SDD_E2E_STRICT": "1"} if strict else None, passthrough)
        if r["status"] == 5:  # pytest: no tests collected
            r.update(status=0, skipped=True, note="no e2e tests collected")
        results.append(r)
    else:
        results.append({"label": "e2e suite", "status": 0, "skipped": True,
                        "note": "no generated tests yet (run: sdd gen-tests <feature>)"})

    features = list_features(root)
    gate_errors = sum(len(verify_feature(root, f, strict)["errors"]) for f in features)
    results.append({"label": f"sdd verify ({len(features)} feature(s))", "status": 1 if gate_errors else 0,
                    "skipped": not features, "note": f"{gate_errors} gate error(s)" if gate_errors else None})

    if pentest_targets:
        p = pentest(root, pentest_targets, authorized=authorized)
        # A requested scan that did not run fails the sweep: skipped is not the same as clean.
        results.append({"label": "sdd pentest", "status": p["status"], "skipped": False,
                        "note": one_line(p["reason"], 160) if p["status"] == NOT_RUN else None})

    return {"results": results, "ok": all(r["status"] == 0 for r in results)}
