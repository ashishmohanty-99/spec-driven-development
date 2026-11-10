import re
import unittest
from pathlib import Path

from specpilot.gentests import gen_tests
from specpilot.regression import regression
from specpilot.security import SecurityError

from .helpers import feature, sdd, tmp, write

ASSETS = Path(__file__).resolve().parent.parent / "specpilot" / "assets"
SPEC = ("Status: approved\n- REQ-001: a\n- REQ-002: b\n## Acceptance scenarios\n"
        '- REQ-001 — Given the user opens /login, when they click "Sign in", then the page shows "Welcome"\n')


class GenTestsTests(unittest.TestCase):
    def setUp(self):
        self.r = tmp()
        sdd(self.r, "init")

    def test_errors_without_spec_or_requirements(self):
        with self.assertRaises(SecurityError):
            gen_tests(self.r, "missing")
        feature(self.r, "empty", spec="Status: draft\nnothing")
        with self.assertRaises(SecurityError):
            gen_tests(self.r, "empty")

    def test_generates_valid_traceable_python(self):
        feature(self.r, spec=SPEC)
        result = gen_tests(self.r, "f1")
        source = result["file"].read_text()
        compile(source, "t", "exec")
        self.assertEqual(result["file"].name, "test_f1.py")
        self.assertIn("@pytest.mark.requirement('REQ-001')", source)
        self.assertIn("given='the user opens /login'", source)
        self.assertIn("missing('REQ-002: no acceptance scenario", source)
        self.assertEqual(result["missing"], ["REQ-002"])

    def test_regeneration_keeps_handwritten_tests(self):
        feature(self.r, spec=SPEC)
        path = gen_tests(self.r, "f1")["file"]
        with open(path, "a") as fh:
            fh.write("\ndef test_handwritten(page):\n    pass\n")
        feature(self.r, spec=SPEC + "- REQ-003: c\n")
        self.assertFalse(gen_tests(self.r, "f1")["created"])
        source = path.read_text()
        self.assertIn("test_handwritten", source)
        self.assertIn("REQ-003", source)

    def test_generated_tests_satisfy_strict_traceability(self):
        feature(self.r, spec=SPEC, plan="# p", tasks="- [x] T-001 x (covers: REQ-001, REQ-002)")
        self.assertEqual(sdd(self.r, "verify", "f1", "--strict")[0], 1)
        self.assertEqual(sdd(self.r, "gen-tests", "f1")[0], 0)
        self.assertEqual(sdd(self.r, "verify", "f1", "--strict")[0], 0)


class ConnectorTests(unittest.TestCase):
    """The connector's step matching is plain regex logic, testable without a browser."""

    def test_builtin_steps_match_documented_phrasings(self):
        source = (ASSETS / "e2e" / "ui_connector.py").read_text()
        patterns = [re.compile(p, re.IGNORECASE) for p in re.findall(r"@step\(r'(.+)'\)\n", source)]
        self.assertGreaterEqual(len(patterns), 7)
        for phrase in ("the user opens /login", "the user is logged in", "they are logged in as admin",
                       'they click "Sign in"', 'they fill "bad" into "Password"', 'the page shows "Welcome"',
                       'the page does not show "Error"', "the url contains /dashboard"):
            self.assertTrue(any(p.fullmatch(phrase) for p in patterns), phrase)
        self.assertNotRegex(source, r"(?i)password\s*=\s*['\"]")


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.r = tmp()
        sdd(self.r, "init")

    def test_clean_project_passes_with_skips(self):
        result = regression(self.r)
        self.assertTrue(result["ok"])
        self.assertTrue(all(x["skipped"] for x in result["results"]))

    def test_runs_configured_command_without_shell(self):
        write(self.r, ".sdd/config.json", '{"commands": {"test": "python3 -c \\"import sys; sys.exit(0)\\" ; touch pwned"}}')
        result = regression(self.r)
        self.assertTrue(result["ok"])
        self.assertFalse((self.r / "pwned").exists())  # `;` was an argument, not a shell operator
        write(self.r, ".sdd/config.json", '{"commands": {"test": "python3 -c \\"import sys; sys.exit(4)\\""}}')
        self.assertFalse(regression(self.r)["ok"])

    def test_gate_failure_and_unrun_pentest_fail_the_sweep(self):
        feature(self.r, "bad", spec="Status: approved\n- REQ-001: a", tasks="- [ ] T-001 x")
        self.assertFalse(regression(self.r)["ok"])
        r2 = tmp()
        sdd(r2, "init")
        result = regression(r2, pentest_targets=["."])
        self.assertFalse(result["ok"])
        self.assertEqual(result["results"][-1]["status"], 3)


class AssetLintTests(unittest.TestCase):
    """Every shipped skill, command and agent follows the frontmatter contract."""

    @staticmethod
    def front(path):
        m = re.match(r"^---\n(.*?)\n---\n", path.read_text(), flags=re.DOTALL)
        return dict(l.split(":", 1) for l in m.group(1).splitlines() if ":" in l) if m else None

    def test_skills(self):
        names = set()
        for d in sorted((ASSETS / "skills").iterdir()):
            fm = self.front(d / "SKILL.md")
            text = (d / "SKILL.md").read_text()
            self.assertIsNotNone(fm, d.name)
            self.assertEqual(fm["name"].strip(), d.name)
            self.assertRegex(fm["description"], r"\bUse (when|at|after|before|on|in)\b", d.name)
            self.assertLessEqual(len(fm["description"]), 1024)
            for section in ("## Overview", "## Common Rationalizations", "## Red Flags", "## Verification"):
                self.assertIn(section, text, f"{d.name}: {section}")
            self.assertNotIn("npx ", text, d.name)
            names.add(d.name)
        for f in list((ASSETS / "commands").glob("*.md")) + list((ASSETS / "skills").rglob("*.md")):
            for ref in re.findall(r"`([a-z][a-z-]+)` skill", f.read_text()):
                self.assertIn(ref, names, f"{f.name} references unknown skill {ref}")

    def test_commands_and_agents(self):
        for kind in ("commands", "agents"):
            for f in (ASSETS / kind).glob("*.md"):
                fm = self.front(f)
                self.assertTrue(fm and fm.get("description", "").strip(), f.name)


if __name__ == "__main__":
    unittest.main()
