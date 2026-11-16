"""Guided setup: work out what the tool could not detect, and ask only that.

`questions()` returns the open questions in the order they should be asked. Each has plain-language
text, the reason it matters, options with a recommended default, and is answered with
`sdd answer <id> <value>`. Nothing here is required: every question has a safe default.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .gentests import detect_framework
from .security import SecurityError, has_control_chars, one_line, read_text
from .spec import E2E_FRAMEWORKS, LIFECYCLE, load_config, save_config

STACK_HINT = ("for example: 'React + TypeScript web app with a FastAPI backend', 'Spring Boot REST API', "
              "'Flutter mobile app', 'Go CLI tool'")


def _profile(root: Path) -> dict:
    try:
        data = json.loads(read_text(Path(root) / ".sdd" / "codebase-profile.json") or "{}")
    except ValueError:
        data = {}
    return data if isinstance(data, dict) else {}


def catalogue(root: Path) -> list[dict]:
    """Every setup question, each with a detected default."""
    cfg, profile = load_config(root), _profile(root)
    greenfield = not profile.get("languages")
    detected_test = (profile.get("commands") or {}).get("test")
    fw = detect_framework(root)
    fw_label = {"playwright-python": "Playwright with Python (pytest)",
                "playwright-ts": "Playwright with TypeScript",
                "gherkin": "Gherkin feature files (works with Java, C#, Go, Ruby, PHP, Rust, mobile and others)"}
    items = []
    if greenfield:
        items.append({
            "id": "stack", "key": "project.stack", "kind": "text",
            "question": "This repository has no code yet. What are you building, and with what?",
            "why": f"It decides the folder structure and tooling that get set up ({STACK_HINT}).",
            "recommended": None, "options": []})
    items.append({
        "id": "test-command", "key": "commands.test", "kind": "text",
        "question": "What command runs your automated tests?",
        "why": "It is run by `sdd regression` and in CI. Answer 'none' if there are no tests yet.",
        "recommended": detected_test, "options": [detected_test] if detected_test else []})
    items.append({
        "id": "e2e-framework", "key": "e2eFramework", "kind": "choice",
        "question": "Which form should generated acceptance tests take?",
        "why": "Tests are generated from each spec's Given/When/Then scenarios in the form your stack can run.",
        "recommended": fw,
        "options": [{"value": name, "label": fw_label[name]} for name in E2E_FRAMEWORKS]})
    items.append({
        "id": "base-url", "key": "baseUrl", "kind": "text",
        "question": "Where does the application run locally (the address browser tests should open)?",
        "why": "Browser tests need a starting address. Answer 'none' for a library, CLI or API-only project.",
        "recommended": "http://localhost:3000", "options": ["http://localhost:3000", "none"]})
    items.append({
        "id": "lifecycle", "key": "lifecycle", "kind": "checks",
        "question": "Keep the full lifecycle, or switch any optional check off?",
        "why": "Every check is on by default. Each one can be switched off, at the cost shown beside it.",
        "recommended": "all",
        "options": [{"value": name, "label": title, "skipping_means": cost}
                    for name, (title, _what, cost) in LIFECYCLE.items()]})
    answered = set(cfg["onboarding"].get("answered", []))
    for item in items:
        item["answered"] = item["id"] in answered
    return items


def questions(root: Path) -> list[dict]:
    return [q for q in catalogue(root) if not q["answered"]]


def _mark(cfg: dict, qid: str) -> None:
    done = cfg["onboarding"].setdefault("answered", [])
    if qid not in done:
        done.append(qid)


def answer(root: Path, qid: str, value: str) -> str:
    """Record one answer. Returns a one-line confirmation."""
    cfg = load_config(root)
    known = {q["id"]: q for q in catalogue(root)}
    if qid not in known:
        raise SecurityError(f'unknown question "{one_line(qid, 40)}" (see: sdd questions)')
    value = (value or "").strip()
    if not value or len(value) > 300 or any(ch in value for ch in "\n\r\0"):
        raise SecurityError("answer must be one line of at most 300 characters")
    none = value.lower() in ("none", "no", "n/a", "skip")

    if qid == "stack":
        cfg["project"]["stack"] = one_line(value, 200)
        message = f"Stack recorded: {cfg['project']['stack']}"
    elif qid == "test-command":
        cfg["commands"]["test"] = None if none else value
        message = "No test command yet." if none else f"Tests run with: {value}"
    elif qid == "e2e-framework":
        if value not in E2E_FRAMEWORKS:
            raise SecurityError(f"choose one of: {', '.join(E2E_FRAMEWORKS)}")
        cfg["e2eFramework"] = value
        message = f"Acceptance tests will be generated as: {value}"
    elif qid == "base-url":
        if none:
            cfg["baseUrl"] = None
            message = "No local address; browser steps will be reported as gaps until one is set."
        else:
            if has_control_chars(value) or not re.fullmatch(r"https?://[A-Za-z0-9.\-]+(:\d{1,5})?(/[^\s]*)?", value):
                raise SecurityError("base URL must look like http://localhost:3000")
            cfg["baseUrl"] = value.rstrip("/")
            message = f"Browser tests will open: {cfg['baseUrl']}"
    else:  # lifecycle: "all" keeps everything; anything else is handled by `sdd lifecycle skip`
        if value.lower() != "all":
            raise SecurityError('answer "all" to keep every check, or use: sdd lifecycle skip <check> --reason "..."')
        message = "Full lifecycle kept: every check is on."
    _mark(cfg, qid)
    save_config(root, cfg)
    return message
