"""Guided setup, lifecycle switches, next-step guidance and language-neutral test generation."""
import json
import shutil
import subprocess
import unittest

from specpilot.gentests import detect_framework, gen_tests
from specpilot.onboarding import answer, questions
from specpilot.regression import regression
from specpilot.security import SecurityError
from specpilot.spec import LIFECYCLE, load_config, verify_feature

from .helpers import feature, sdd, tmp, write

SPEC = ('Status: approved\n- REQ-001: a\n- REQ-002: b\n## Acceptance scenarios\n'
        '- REQ-001 — Given the user opens /login, when they click "Sign in", then the page shows "Welcome"\n')


def repo(**files):
    r = tmp()
    for name, body in files.items():
        write(r, name, body)
    sdd(r, "init")
    return r


class GuidedSetup(unittest.TestCase):
    def test_empty_repository_is_greenfield_and_asks_for_the_stack(self):
        r = repo()
        self.assertEqual(load_config(r)["project"]["kind"], "greenfield")
        ids = [q["id"] for q in questions(r)]
        self.assertEqual(ids, ["stack", "test-command", "e2e-framework", "base-url", "lifecycle"])
        code, out = sdd(r, "next")
        self.assertEqual(code, 0)
        self.assertIn("/sdd-scaffold", out)

    def test_existing_repository_is_not_asked_what_it_already_shows(self):
        r = repo(**{"pyproject.toml": '[project]\ndependencies=["pytest"]', "app/main.py": "x = 1"})
        self.assertEqual(load_config(r)["project"]["kind"], "existing")
        qs = {q["id"]: q for q in questions(r)}
        self.assertNotIn("stack", qs)
        self.assertEqual(qs["test-command"]["recommended"], "pytest")
        self.assertEqual(qs["e2e-framework"]["recommended"], "playwright-python")

    def test_answers_are_validated_recorded_and_not_asked_again(self):
        r = repo()
        answer(r, "stack", "Spring Boot REST API")
        answer(r, "test-command", "mvn -q test")
        answer(r, "e2e-framework", "gherkin")
        answer(r, "base-url", "none")
        answer(r, "lifecycle", "all")
        cfg = load_config(r)
        self.assertEqual((cfg["project"]["stack"], cfg["commands"]["test"], cfg["e2eFramework"], cfg["baseUrl"]),
                         ("Spring Boot REST API", "mvn -q test", "gherkin", None))
        self.assertEqual(questions(r), [])
        self.assertIn("Setup is complete", sdd(r, "questions")[1])
        for qid, bad in (("e2e-framework", "selenium"), ("base-url", "javascript:alert(1)"), ("base-url", "http://a b"),
                         ("nope", "x"), ("test-command", "a\nb"), ("lifecycle", "none")):
            with self.assertRaises(SecurityError, msg=(qid, bad)):
                answer(r, qid, bad)

    def test_questions_json_is_machine_readable_for_agents(self):
        r = repo()
        code, out = sdd(r, "questions", "--json")
        data = json.loads(out)
        self.assertEqual(code, 0)
        lifecycle = next(q for q in data if q["id"] == "lifecycle")
        self.assertEqual({o["value"] for o in lifecycle["options"]}, set(LIFECYCLE))
        self.assertTrue(all(o["skipping_means"] for o in lifecycle["options"]))


class LifecycleSwitches(unittest.TestCase):
    def setUp(self):
        self.r = repo()

    def test_skip_needs_a_reason_warns_and_is_shown_on_every_report(self):
        code, out = sdd(self.r, "lifecycle", "skip", "plan")
        self.assertEqual(code, 1)
        self.assertIn("needs a reason", out)
        code, out = sdd(self.r, "lifecycle", "skip", "plan", "--reason", "two-person prototype")
        self.assertEqual(code, 0)
        self.assertIn("WARNING", out)
        self.assertIn(LIFECYCLE["plan"][2], out)
        cfg = load_config(self.r)
        self.assertFalse(cfg["lifecycle"]["plan"])
        self.assertEqual(cfg["skipped"]["plan"]["reason"], "two-person prototype")
        feature(self.r, spec="Status: approved\n- REQ-001: a")
        for cmd in (["status"], ["verify"], ["next"], ["regression"], ["doctor"]):
            self.assertIn("Switched off by the team", sdd(self.r, *cmd)[1], cmd)
        self.assertEqual(sdd(self.r, "lifecycle", "enable", "plan")[0], 0)
        self.assertNotIn("Switched off", sdd(self.r, "status")[1])
        self.assertEqual(load_config(self.r)["skipped"], {})

    def test_unknown_check_and_spec_step_cannot_be_switched(self):
        for name in ("spec", "specify", "everything"):
            self.assertEqual(sdd(self.r, "lifecycle", "skip", name, "--reason", "because we can")[0], 1)
        write(self.r, ".sdd/config.json", json.dumps({"lifecycle": {"spec": False}}))
        self.assertEqual(sdd(self.r, "status")[0], 1)

    def test_each_switch_changes_exactly_its_own_gate(self):
        spec = "Status: approved\n- REQ-001: a\n- REQ-002: b [NEEDS CLARIFICATION: q]"
        feature(self.r, spec=spec, tasks="- [x] T-001 x (covers: REQ-001)")
        errors = "\n".join(verify_feature(self.r, "f1", strict=True)["errors"])
        for expected in ("NEEDS CLARIFICATION", "without plan.md", "REQ-002 is not covered", "REQ-001 has completed"):
            self.assertIn(expected, errors)

        def errors_with(check):
            sdd(self.r, "lifecycle", "skip", check, "--reason", "testing the switch")
            found = "\n".join(verify_feature(self.r, "f1", strict=True)["errors"])
            sdd(self.r, "lifecycle", "enable", check)
            return found

        self.assertNotIn("NEEDS CLARIFICATION", errors_with("clarify"))
        self.assertNotIn("without plan.md", errors_with("plan"))
        self.assertNotIn("is not covered", errors_with("tasks"))
        self.assertNotIn("has completed", errors_with("tests"))
        self.assertIn("REQ-002 is not covered", errors_with("plan"), "skipping one check leaves the others on")

    def test_secret_scan_and_e2e_switches(self):
        key = "sk-" + "Q1w2E3r4" * 4
        feature(self.r, spec=f"Status: draft\n- REQ-001: a\nkey {key}")
        self.assertTrue(any("SECURITY" in e for e in verify_feature(self.r, "f1")["errors"]))
        sdd(self.r, "lifecycle", "skip", "secrets", "--reason", "scanned by another tool")
        self.assertFalse(any("SECURITY" in e for e in verify_feature(self.r, "f1")["errors"]))
        self.assertEqual(sdd(self.r, "audit")[0], 1, "an explicit audit still scans")
        sdd(self.r, "lifecycle", "skip", "e2e", "--reason", "library, no user interface")
        row = next(x for x in regression(self.r)["results"] if x["label"] == "acceptance tests")
        self.assertTrue(row["skipped"])
        self.assertIn("switched off", row["note"])

    def test_shipped_gate_respects_the_switches(self):
        feature(self.r, spec="Status: shipped\n- REQ-001: a", plan="# p")
        self.assertTrue(verify_feature(self.r, "f1")["errors"])
        for check in ("tasks", "tests"):
            sdd(self.r, "lifecycle", "skip", check, "--reason", "prototype only")
        self.assertEqual(verify_feature(self.r, "f1")["errors"], [])


class NextStep(unittest.TestCase):
    def test_walks_a_feature_through_every_phase(self):
        r = repo(**{"pyproject.toml": '[project]\ndependencies=["pytest"]', "app/main.py": "x = 1"})
        self.assertIn("sdd init", sdd(tmp(), "next")[1])

        def nxt():
            return sdd(r, "next")[1]

        self.assertIn("/sdd-spec", nxt())
        feature(r, spec="Status: draft\n- REQ-001: a [NEEDS CLARIFICATION: q]")
        self.assertIn("/sdd-clarify f1", nxt())
        feature(r, spec="Status: draft\n- REQ-001: a")
        self.assertIn("sets `Status: approved`", nxt())
        feature(r, spec="Status: approved\n- REQ-001: a")
        self.assertIn("/sdd-plan f1", nxt())
        feature(r, plan="# p")
        self.assertIn("/sdd-tasks f1", nxt())
        feature(r, tasks="- [ ] T-001 x (covers: REQ-001)\n- [ ] T-002 y (covers: REQ-001)")
        self.assertIn("Build task 1 of 2", nxt())
        feature(r, tasks="- [x] T-001 x (covers: REQ-001)\n- [x] T-002 y (covers: REQ-001)")
        self.assertIn("/sdd-gen-tests f1", nxt())
        write(r, "tests/test_f1.py", "# REQ-001")
        self.assertIn("/sdd-verify f1", nxt())
        write(r, ".sdd/specs/f1/verification.md", "ok")
        self.assertIn("/sdd-ship f1", nxt())
        feature(r, spec="Status: shipped\n- REQ-001: a")
        self.assertIn("Nothing to do", nxt())

    def test_skipped_phases_are_not_suggested(self):
        r = repo()
        for check in ("plan", "tasks"):
            sdd(r, "lifecycle", "skip", check, "--reason", "solo prototype")
        feature(r, spec="Status: approved\n- REQ-001: a")
        out = sdd(r, "next")[1]
        self.assertIn("/sdd-build f1", out)
        self.assertNotIn("/sdd-plan", out)


class AnyLanguage(unittest.TestCase):
    def test_framework_follows_the_codebase(self):
        cases = (({"src/a.ts": "x", "src/b.ts": "x", "package.json": "{}"}, "playwright-ts"),
                 ({"app/a.py": "x"}, "playwright-python"),
                 ({"src/main/java/A.java": "x", "pom.xml": "<p/>"}, "gherkin"),
                 ({"cmd/main.go": "x", "go.mod": "m"}, "gherkin"),
                 ({"src/main.rs": "x", "Cargo.toml": "c"}, "gherkin"),
                 ({"App/Program.cs": "x", "App/App.csproj": "x"}, "gherkin"),
                 ({}, "gherkin"))
        for files, expected in cases:
            self.assertEqual(detect_framework(repo(**files)), expected, files)

    def test_typescript_form_is_traceable_inert_and_valid(self):
        r = repo(**{"src/a.ts": "x", "package.json": "{}"})
        evil = 'Given `${process.exit(1)}` </script>\\", when "); process.exit(1); (", then c'
        feature(r, spec=SPEC + f"- REQ-002 — {evil}\n", plan="# p", tasks="- [x] T-001 x (covers: REQ-001, REQ-002)")
        out = gen_tests(r, "f1")
        source = out["file"].read_text()
        self.assertEqual(out["file"].name, "f1.spec.ts")
        self.assertTrue((r / "tests/e2e/ui-connector.ts").is_file())
        self.assertIn('test("REQ-001 #1:', source)
        body = source.split("GENERATED-BEGIN")[1].split("\n", 1)[1]
        self.assertIn("REQ-002 #1: Given", body, "the hostile scenario was generated, not dropped")
        self.assertEqual(body.count("process.exit"), 4, "present only as text inside string literals")
        self.assertNotIn("</script", source)
        for line in body.splitlines():  # every line that carries spec text is one complete string literal
            if "process.exit" in line:
                self.assertRegex(line, r'^(test\(|    (given|when|then): )"(?:[^"\\]|\\.)*"(, async \(\{ page \}\) => \{|,)$')
        self.assertEqual(verify_feature(r, "f1", strict=True)["errors"], [])
        node = shutil.which("node")
        if node:  # the generated file is plain JavaScript syntax, so node can parse it
            check = out["file"].with_suffix(".mjs")
            check.write_text(source)
            done = subprocess.run([node, "--check", str(check)], capture_output=True, text=True, check=False)
            self.assertEqual(done.returncode, 0, done.stderr)

    def test_typescript_gaps_do_not_count_as_proof(self):
        r = repo(**{"src/a.ts": "x", "package.json": "{}"})
        feature(r, spec=SPEC, plan="# p", tasks="- [x] T-001 x (covers: REQ-001, REQ-002)")
        gen_tests(r, "f1")
        errors = "\n".join(verify_feature(r, "f1", strict=True)["errors"])
        self.assertIn("REQ-002 has completed", errors)
        self.assertNotIn("REQ-001 has completed", errors)

    def test_gherkin_form_for_any_other_stack(self):
        r = repo(**{"src/main/java/A.java": "x", "pom.xml": "<p/>"})
        feature(r, spec=SPEC + "- REQ-002 — Given a\tb, when c, then d\n", plan="# p",
                tasks="- [x] T-001 x (covers: REQ-001, REQ-002)")
        out = gen_tests(r, "f1")
        text = out["file"].read_text()
        self.assertEqual(out["file"].name, "f1.feature")
        self.assertIn("Feature: f1", text)
        self.assertRegex(text, r"  @REQ-001\n  Scenario: REQ-001 #1 .*\n    Given the user opens /login\n    When .*\n    Then ")
        self.assertIsNone(out["command"], "the Cucumber runner's command is the project's to set")
        self.assertEqual(verify_feature(r, "f1", strict=True)["errors"], [])
        # until commands.e2e is set, a strict regression fails rather than pretending they ran
        row = next(x for x in regression(r, strict=True)["results"] if x["label"] == "acceptance tests")
        self.assertEqual(row["status"], 1)
        # regeneration keeps hand-written scenarios; a gap is never proof
        with open(out["file"], "a") as fh:
            fh.write("\n  Scenario: mine\n    Given x\n")
        feature(r, spec=SPEC)
        text = gen_tests(r, "f1")["file"].read_text()
        self.assertIn("Scenario: mine", text)
        self.assertIn("# GAP REQ-002", text)
        self.assertIn("REQ-002 has completed", "\n".join(verify_feature(r, "f1", strict=True)["errors"]))

    def test_documentation_in_the_test_folder_is_not_a_test(self):
        r = repo(**{"src/main/java/A.java": "x"})
        write(r, "tests/e2e/NOTES.md", "REQ-001 is covered, honest")
        feature(r, spec="Status: approved\n- REQ-001: a", plan="# p", tasks="- [x] T-001 x (covers: REQ-001)")
        self.assertTrue(verify_feature(r, "f1", strict=True)["errors"])


if __name__ == "__main__":
    unittest.main()
