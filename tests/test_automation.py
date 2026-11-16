import re
import unittest
from pathlib import Path

from specpilot.gentests import gen_tests
from specpilot.regression import regression
from specpilot.security import SecurityError

from .helpers import feature, sdd, tmp, use_python_e2e, write

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "spec-driven-development-by-ashishmohanty"
ASSETS = SKILL / "scripts" / "specpilot" / "assets"
SPEC = ("Status: approved\n- REQ-001: a\n- REQ-002: b\n## Acceptance scenarios\n"
        '- REQ-001 — Given the user opens /login, when they click "Sign in", then the page shows "Welcome"\n')


class GenTestsTests(unittest.TestCase):
    def setUp(self):
        self.r = tmp()
        sdd(self.r, "init")
        use_python_e2e(self.r)

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
        # REQ-001 has a real scenario; REQ-002 only has a placeholder stub, which proves nothing.
        code, out = sdd(self.r, "verify", "f1", "--strict")
        self.assertEqual(code, 1)
        self.assertIn("REQ-002 has completed task(s) but no test file names it", out)
        self.assertNotIn("REQ-001 has completed", out)
        feature(self.r, spec=SPEC + '- REQ-002 — Given the user opens /a, when they click "B", then the page shows "C"\n')
        sdd(self.r, "gen-tests", "f1")
        self.assertEqual(sdd(self.r, "verify", "f1", "--strict")[0], 0)


class ConnectorTests(unittest.TestCase):
    """The connector's step matching is plain regex logic, testable without a browser."""

    def test_builtin_steps_match_documented_phrasings(self):
        source = (ASSETS / "e2e" / "playwright-python" / "ui_connector.py").read_text()
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
            fm = self.front(d / "PHASE.md")
            text = (d / "PHASE.md").read_text()
            self.assertIsNotNone(fm, d.name)
            self.assertEqual(fm["name"].strip(), d.name)
            self.assertRegex(fm["description"], r"\bUse (when|at|after|before|on|in)\b", d.name)
            self.assertLessEqual(len(fm["description"]), 1024)
            for section in ("## Overview", "## Common Rationalizations", "## Red Flags", "## Verification"):
                self.assertIn(section, text, f"{d.name}: {section}")
            self.assertNotIn("npx specpilot", text, d.name)
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


class DistributionTests(unittest.TestCase):
    """skills/spec-driven-development-by-ashishmohanty/ is the product: it must be a valid skill and work when copied anywhere."""

    def test_skill_folder_is_a_valid_self_contained_skill(self):
        fm = AssetLintTests.front(SKILL / "SKILL.md")
        self.assertEqual(fm["name"].strip(), "spec-driven-development-by-ashishmohanty")
        self.assertLessEqual(set(fm), {"name", "description", "license", "compatibility", "metadata", "allowed-tools"})
        self.assertLessEqual(len(fm["description"].strip()), 1024)
        text = (SKILL / "SKILL.md").read_text()
        for ref in re.findall(r"`(references/[\w-]+\.md)`", text):
            self.assertTrue((SKILL / ref).is_file(), ref)
        self.assertTrue((SKILL / "LICENSE").is_file())
        self.assertEqual((SKILL / "LICENSE").read_text(), (ROOT / "LICENSE").read_text())

    def test_installed_copy_runs_with_nothing_else_available(self):
        import shutil
        import subprocess
        import sys

        installed = tmp() / "skills" / "spec-driven-development-by-ashishmohanty"  # what `npx skills add` or an unzip leaves behind
        shutil.copytree(SKILL, installed, ignore=shutil.ignore_patterns("__pycache__"))
        project = tmp()
        env = {"PATH": "/usr/bin:/bin"}  # no PYTHONPATH: only the copy is importable
        run = subprocess.run([sys.executable, str(installed / "scripts" / "sdd.py"), "--dir", str(project),
                              "init", "--vendor"], env=env, capture_output=True, text=True, check=False)
        self.assertEqual(run.returncode, 0, run.stderr)
        for cmd in ("doctor", "audit", "status"):
            vendored = subprocess.run([sys.executable, ".sdd/bin/sdd.py", cmd], cwd=project, env=env,
                                      capture_output=True, text=True, check=False)
            self.assertEqual(vendored.returncode, 0, f"{cmd}: {vendored.stdout}{vendored.stderr}")
        self.assertIn("python3 .sdd/bin/sdd.py", (project / "CLAUDE.md").read_text())

    def test_only_the_entry_skill_is_discoverable_at_the_top_level(self):
        # Installers list skills/<name>/SKILL.md; the phase skills are installed per project by `sdd init`.
        self.assertEqual([p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")], ["spec-driven-development-by-ashishmohanty"])
        # The directory build under plugin/ is separate; installers and the upload zip read skills/ only.
        self.assertEqual(len(list((ROOT / "skills").rglob("SKILL.md"))), 1)

    def test_zip_for_upload_is_reproducible_and_complete(self):
        import sys
        import zipfile

        sys.path.insert(0, str(ROOT / "tools"))
        import build_skill

        archive = build_skill.build(tmp())
        names = zipfile.ZipFile(archive).namelist()
        for expected in ("SKILL.md", "scripts/sdd.py", "references/Security-Model.md", "scripts/specpilot/cli.py"):
            self.assertIn("spec-driven-development-by-ashishmohanty/" + expected, names)
        self.assertEqual([n for n in names if n.upper().endswith("SKILL.MD")],
                         ["spec-driven-development-by-ashishmohanty/SKILL.md"], "upload hosts allow exactly one")
        self.assertFalse([n for n in names if "__pycache__" in n or not n.startswith("spec-driven-development-by-ashishmohanty/")])
        self.assertEqual(archive.read_bytes(), build_skill.build(tmp()).read_bytes())


class WalkthroughRegressionTests(unittest.TestCase):
    def setUp(self):
        self.r = tmp()
        sdd(self.r, "init")
        use_python_e2e(self.r)

    def test_template_placeholder_scenarios_do_not_become_tests(self):
        sdd(self.r, "new", "f1")
        source = gen_tests(self.r, "f1")["file"].read_text()
        self.assertNotIn("run_scenario(\n", source)
        self.assertIn("missing('REQ-001", source)

    def test_dir_option_works_before_and_after_the_command(self):
        self.assertEqual(sdd(self.r, "status")[0], 0)
        import contextlib
        import io

        from specpilot.cli import main
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["status", "--dir", str(self.r)]), 0)

    def test_conftest_reports_missing_playwright_clearly(self):
        text = (self.r / "tests/e2e/conftest.py").read_text()
        self.assertIn("pytest-playwright is not installed", text)
        compile(text, "conftest.py", "exec")


class DocsTests(unittest.TestCase):
    def test_every_test_cited_in_the_security_model_exists(self):
        root = ROOT
        cited = set(re.findall(r"`(test_[a-z0-9_]+)`", (SKILL / "references" / "Security-Model.md").read_text()))
        defined = set()
        for f in (root / "tests").glob("test_*.py"):
            defined |= set(re.findall(r"def (test_\w+)", f.read_text()))
        self.assertGreater(len(cited), 20)
        self.assertEqual(sorted(cited - defined), [])

    def test_documented_counts_match_the_assets(self):
        home = (ROOT / "wiki" / "Home.md").read_text()
        self.assertIn(f"{len(list((ASSETS / 'skills').iterdir()))} skills", home)
        self.assertIn(f"{len(list((ASSETS / 'commands').glob('*.md')))} slash commands", home)


class DirectoryPluginTests(unittest.TestCase):
    """plugin/ is what a public plugin directory reviews: documentation only, always in sync."""

    @classmethod
    def setUpClass(cls):
        import sys
        sys.path.insert(0, str(ROOT / "tools"))
        import build_plugin
        cls.bp = build_plugin
        cls.plugin = ROOT / "plugin"

    def test_committed_folder_matches_the_sources(self):
        fresh = self.bp.snapshot(self.bp.build(tmp()))
        self.assertEqual(sorted(fresh), sorted(self.bp.snapshot(self.plugin)))
        self.assertEqual(fresh, self.bp.snapshot(self.plugin), "run: python3 tools/build_plugin.py")

    def test_contains_only_file_types_a_directory_accepts(self):
        self.assertEqual(self.bp.problems(self.plugin), [])
        suffixes = {p.suffix.lower() for p in self.plugin.rglob("*") if p.is_file() and p.name != "LICENSE"}
        self.assertLessEqual(suffixes, {".md", ".json", ".png"})
        self.assertFalse(list(self.plugin.rglob("*.py")) + list(self.plugin.rglob("*.ts")))

    def test_manifest_icon_and_readme_meet_the_listing_rules(self):
        import json
        import struct
        manifest = json.loads((self.plugin / ".claude-plugin" / "plugin.json").read_text())
        for field in ("name", "version", "description", "author", "license", "icon"):
            self.assertTrue(manifest.get(field), field)
        self.assertRegex(manifest["name"], r"^[a-z0-9]+(-[a-z0-9]+)*$")
        png = (self.plugin / ".claude-plugin" / "icon.png").read_bytes()
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", png[16:24])
        self.assertEqual(width, height)
        self.assertTrue(512 <= width <= 2048 and len(png) < 2_000_000)
        self.assertGreaterEqual(len((self.plugin / "README.md").read_text().split()), 40)
        self.assertTrue((self.plugin / "LICENSE").is_file())

    def test_no_credential_variables_download_and_run_lines_or_script_paths(self):
        for path in self.plugin.rglob("*.md"):
            text = path.read_text()
            self.assertNotIn("LLM_API_KEY", text, path.name)
            self.assertNotRegex(text, r"curl [^\n]*\|\s*(ba)?sh", path.name)
            self.assertNotIn("${{ secrets.", text, path.name)
        entry = (self.plugin / "skills" / "spec-driven-development-by-ashishmohanty" / "SKILL.md").read_text()
        self.assertNotIn("scripts/", entry)
        self.assertIn("Manual-Mode.md", entry)

    def test_every_skill_is_valid_and_every_reference_resolves(self):
        names = set()
        for skill in sorted((self.plugin / "skills").iterdir()):
            fm = AssetLintTests.front(skill / "SKILL.md")
            self.assertEqual(fm["name"].strip(), skill.name)
            self.assertLessEqual(len(fm["description"].strip()), 1024)
            names.add(skill.name)
        self.assertEqual(len(names), 16)
        entry = self.plugin / "skills" / "spec-driven-development-by-ashishmohanty"
        for ref in re.findall(r"`(references/[\w-]+\.md)`", (entry / "SKILL.md").read_text()):
            self.assertTrue((entry / ref).is_file(), ref)
        manual = (entry / "references" / "Manual-Mode.md").read_text()
        for template in re.findall(r"`(templates/[\w-]+\.md)`", manual):
            self.assertTrue((entry / template).is_file(), template)
        for command in (self.plugin / "commands").glob("*.md"):
            for used in re.findall(r"`([a-z][a-z-]+)` skill", command.read_text()):
                self.assertIn(used, names, f"{command.name} -> {used}")
