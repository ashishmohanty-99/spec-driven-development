"""UI connector: the single place where spec language meets your application's UI.

Generated tests (test_<feature>.py) never contain selectors. They hand each Given / When / Then
phrase from spec.md to this module, which finds a matching *step* and runs it with Playwright.

Add your own steps at the bottom with @step. A step is a regular expression plus a function:

    @step(r'the cart shows (?P<count>\\d+) items?')
    def cart_count(page, count):
        expect(page.get_by_test_id("cart-count")).to_have_text(count)

Security rules for this file:
  * never hard-code credentials; read them from environment variables;
  * SDD_BASE_URL must be http(s); point it only at environments you are allowed to test.
"""
from __future__ import annotations

import importlib.util
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import pytest

try:  # Playwright is only needed when the suite actually runs.
    from playwright.sync_api import expect
except ImportError:  # pragma: no cover
    expect = None

BASE_URL = os.environ.get("SDD_BASE_URL", "http://localhost:3000").rstrip("/")
STRICT = os.environ.get("SDD_E2E_STRICT") == "1"
_STEPS: list = []


def _check_base_url() -> None:
    parsed = urlparse(BASE_URL)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        pytest.fail(f"SDD_BASE_URL must be an http(s) URL, got: {BASE_URL!r}")


def step(pattern: str):
    """Register a step. Patterns are matched case-insensitively against the whole phrase."""
    def register(fn):
        _STEPS.append((re.compile(pattern, re.IGNORECASE), fn))
        return fn
    return register


def missing(reason: str) -> None:
    """A gap in coverage: skipped locally so you can see it, failed under SDD_E2E_STRICT=1 (CI)."""
    if STRICT:
        pytest.fail(reason)
    pytest.skip(reason)


def run_step(page, phrase: str) -> None:
    text = phrase.strip().rstrip(".")
    for part in re.split(r"\s+and\s+(?=(?:the|a|an|they|user|I)\b)", text, flags=re.IGNORECASE):
        for pattern, fn in _STEPS:
            match = pattern.fullmatch(part.strip())
            if match:
                fn(page, **match.groupdict())
                break
        else:
            missing(f"no UI step matches: {part.strip()!r} (add one with @step in tests/e2e/ui_connector.py)")


def run_scenario(page, given: str, when: str, then: str) -> None:
    _check_base_url()
    for phrase in (given, when, then):
        run_step(page, phrase)


def _project_login():
    """Load .sdd/extensions/ui_login.py if the project provides one."""
    path = Path.cwd() / ".sdd" / "extensions" / "ui_login.py"
    if not path.is_file() or path.is_symlink():
        return None
    spec = importlib.util.spec_from_file_location("sdd_ui_login", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, "login", None)


# ── Built-in steps: scenarios phrased this way run with no extra code ──────────────────────────

@step(r'(?:the |a )?(?:user|visitor|they|I) (?:opens?|visits?|is on|am on|are on) (?:the page )?(?P<path>/\S*)')
def open_page(page, path):
    page.goto(BASE_URL + path)


@step(r'(?:the |a )?(?:user|they|I) (?:is|am|are) (?:logged|signed) in(?: as (?P<role>[\w-]+))?')
def logged_in(page, role=None):
    login = _project_login()
    if login is None:
        missing("scenario needs a logged-in user: copy .sdd/extensions/ui_login.example.py to ui_login.py")
    login(page, BASE_URL, role)


@step(r'(?:the user |they |I )?clicks? "(?P<name>[^"]+)"')
def click(page, name):
    target = page.get_by_role("button", name=name).or_(page.get_by_role("link", name=name))
    target.first.click()


@step(r'(?:the user |they |I )?(?:fills?|enters?|types?) "(?P<value>[^"]*)" (?:in|into) "(?P<label>[^"]+)"')
def fill(page, value, label):
    page.get_by_label(label).fill(value)


@step(r'(?:the page|the user|they|I) (?:shows?|sees?|displays?) "(?P<text>[^"]+)"')
def sees(page, text):
    expect(page.get_by_text(text).first).to_be_visible()


@step(r'(?:the page|the user|they|I) (?:does not|do not|doesn\'t|don\'t) (?:show|see|display) "(?P<text>[^"]+)"')
def not_sees(page, text):
    expect(page.get_by_text(text)).to_have_count(0)


@step(r'the (?:url|address) (?:is|becomes|contains) (?P<path>/\S*)')
def url_is(page, path):
    expect(page).to_have_url(re.compile(re.escape(path)))


# ── Project steps: add yours below ───────────────────────────────────────────────────────────
