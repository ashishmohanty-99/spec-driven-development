"""Full-repository secret scanning, the layered security gate, and red-first proof."""
import json
import os
import subprocess
import unittest
from unittest import mock

from specpilot import secretscan as ss
from specpilot.evidence import prove
from specpilot.evidence import status as proof_status
from specpilot.gentests import gen_tests
from specpilot.regression import regression
from specpilot.security import SecurityError
from specpilot.securitygate import security_gate
from specpilot.spec import verify_feature

from .helpers import feature, sdd, tmp, use_python_e2e, without, write

GH = "ghp_" + "Ab1" * 12            # fixtures assembled at run time, never real credentials
STRIPE = "sk_" + "live_" + "Zz9" * 8
SLACK = "https://hooks.slack.com/services/" + "T00000000/B00000000/" + "x" * 24
SPEC = ('Status: approved\n- REQ-001: a\n## Acceptance scenarios\n'
        '- REQ-001 — Given the user opens /a, when they click "B", then the page shows "C"\n')


def git(root, *args):
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, env=env)


def tool(body: str, name: str):
    """A stand-in executable on PATH."""
    bindir = tmp()
    exe = write(bindir, name, "#!/bin/sh\n" + body + "\n")
    exe.chmod(0o755)
    return {"PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}"}


class Base(unittest.TestCase):
    def setUp(self):
        self.r = tmp()
        sdd(self.r, "init")


class SecretScan(Base):
    def test_provider_tokens_are_detected_and_named(self):
        cases = {"GitHub token": GH, "Stripe secret key": STRIPE, "Slack webhook": SLACK,
                 "Anthropic API key": "sk-ant-" + "a1B2" * 8, "npm access token": "npm_" + "a1B2c3" * 6,
                 "Hugging Face token": "hf_" + "aB3d" * 9, "SendGrid API key": "SG." + "a" * 22 + "." + "b" * 43,
                 "Telegram bot token": "123456789:AA" + "b" * 33, "AWS access key": "AKIA" + "ABCDEFGH" * 2}  # sdd:allow-secret (test fixture)
        for kind, value in cases.items():
            kinds = [k for k, _fp in ss.scan_line(f"value = '{value}'")]
            self.assertIn(kind, kinds, kind)

    def test_ordinary_code_and_placeholders_are_not_flagged(self):
        for line in ("token = request.headers.get('Authorization')", "password = getpass.getpass()",
                     "API_KEY=${API_KEY}", 'api_key: "<your key here>"', "sha = 'a3f5c1d2e4b6a7980c1d2e3f4a5b6c7d8e9f0a1b'",
                     "url = 'https://x-access-token:${GH_TOKEN}@github.com/o/r.git'", "const keyboard = new Keyboard()",
                     "secret_santa_participants = load_people(path_to_the_people_file)"):
            self.assertEqual(ss.scan_line(line), [], line)

    def test_whole_working_tree_is_scanned_not_just_sdd_files(self):
        write(self.r, "src/app/settings.py", f"GITHUB = '{GH}'\n")
        write(self.r, "deploy/values.yaml", f"stripe: {STRIPE}\n")
        found = {(f["kind"], f["file"]) for f in ss.scan_secrets(self.r, history=False)["findings"]}
        self.assertIn(("GitHub token", "src/app/settings.py"), found)
        self.assertIn(("Stripe secret key", "deploy/values.yaml"), found)

    def test_git_history_is_scanned_after_the_secret_was_deleted(self):
        git(self.r, "init", "-q")
        path = write(self.r, "config.py", f"TOKEN = '{GH}'\n")
        git(self.r, "add", "-A")
        git(self.r, "commit", "-qm", "add")
        path.write_text("TOKEN = os.environ['TOKEN']\n")
        git(self.r, "commit", "-qam", "remove")
        self.assertEqual(ss.scan_worktree(self.r), [])
        result = ss.scan_secrets(self.r, history=True)
        self.assertEqual(result["status"], "findings")
        hit = result["findings"][0]
        self.assertEqual((hit["kind"], hit["file"]), ("GitHub token", "config.py"))
        self.assertTrue(hit["where"].startswith("history "))
        self.assertEqual(ss.scan_secrets(self.r, history=False)["status"], "clean")

    def test_secret_files_in_history_are_reported_without_being_read(self):
        git(self.r, "init", "-q")
        write(self.r, "prod.pem", "-----BEGIN PRIVATE KEY-----\nabc\n")  # sdd:allow-secret (test fixture)
        git(self.r, "add", "-f", "prod.pem")
        git(self.r, "commit", "-qm", "oops")
        kinds = [f["kind"] for f in ss.scan_history(self.r)["findings"]]
        self.assertEqual(kinds, ["secret-like file committed"])

    def test_values_never_appear_in_reports(self):
        write(self.r, "a.py", f"x = '{GH}'\ny = '{STRIPE}'\n")
        code, out = sdd(self.r, "security", "--no-history")
        self.assertEqual(code, 2)
        self.assertNotIn(GH, out)
        self.assertNotIn(STRIPE, out)
        self.assertIn("fingerprint", out)
        self.assertNotIn(GH, (self.r / ".sdd/security/latest-gate.json").read_text())

    def test_pragma_allow_list_and_excludes(self):
        write(self.r, "docs/example.md", f"token: {GH}  <!-- sdd:allow-secret -->\n")
        self.assertEqual(ss.scan_secrets(self.r, history=False)["status"], "clean")
        write(self.r, "a.py", f"x = '{GH}'\n")
        result = ss.scan_secrets(self.r, history=False)
        fp = result["findings"][0]["fingerprint"]
        self.assertEqual(sdd(self.r, "security", "allow", fp)[0], 1, "a reason is required")
        self.assertEqual(sdd(self.r, "security", "allow", fp, "--reason", "documented fake token")[0], 0)
        again = ss.scan_secrets(self.r, history=False)
        self.assertEqual((again["status"], again["accepted"]), ("clean", 1))
        write(self.r, "fixtures/keys.txt", f"{STRIPE}\n")
        self.assertEqual(ss.scan_secrets(self.r, history=False)["status"], "findings")
        self.assertEqual(ss.scan_secrets(self.r, history=False, exclude=("fixtures/",))["status"], "clean")
        with self.assertRaises(SecurityError):
            ss.allow(self.r, "not-a-fingerprint", "because")

    def test_lockfiles_binaries_and_vendored_code_are_skipped(self):
        write(self.r, "package-lock.json", f'{{"integrity": "{GH}"}}')
        write(self.r, "node_modules/x/index.js", f"k='{GH}'")
        write(self.r, "logo.png", f"{GH}")
        self.assertEqual(ss.scan_worktree(self.r), [])


class ExternalEngines(Base):
    def test_trufflehog_is_preferred_and_its_output_is_parsed_without_leaking(self):
        line = json.dumps({"DetectorName": "Github", "Verified": True, "Raw": GH,
                           "SourceMetadata": {"Data": {"Git": {"commit": "abcdef1234567890", "file": "a.py", "line": 3}}}})
        env = tool(f"echo \"$@\" > \"{self.r}/args.txt\"\ncat <<'EOT'\n{line}\nnot json\nEOT\nexit 183", "trufflehog")
        with mock.patch.dict(os.environ, env):
            result = ss.scan_secrets(self.r)
        self.assertEqual((result["engine"], result["status"]), ("trufflehog", "findings"))
        hit = result["findings"][0]
        self.assertEqual((hit["kind"], hit["file"], hit["line"]), ("Github (LIVE)", "a.py", 3))
        self.assertNotIn(GH, json.dumps(result))
        args = (self.r / "args.txt").read_text()
        self.assertIn("--no-verification", args, "nothing is sent to a provider unless asked")
        self.assertIn("--no-update", args)
        with mock.patch.dict(os.environ, env):
            ss.scan_secrets(self.r, verify_live=True)
        self.assertNotIn("--no-verification", (self.r / "args.txt").read_text())

    def test_trufflehog_clean_and_failing_runs(self):
        with mock.patch.dict(os.environ, tool("exit 0", "trufflehog")):
            self.assertEqual(ss.scan_secrets(self.r)["status"], "clean")
        with mock.patch.dict(os.environ, tool("exit 7", "trufflehog")):
            self.assertEqual(ss.scan_secrets(self.r)["status"], "error", "a crashed scanner is not a clean scan")

    def test_gitleaks_report_is_read_then_removed(self):
        report = json.dumps([{"RuleID": "github-pat", "File": "a.py", "StartLine": 2, "Commit": "", "Fingerprint": "x"}])
        body = ('while [ $# -gt 0 ]; do [ "$1" = "--report-path" ] && out="$2"; shift; done\n'
                f"cat > \"$out\" <<'EOT'\n{report}\nEOT\nexit 2")
        with mock.patch.dict(os.environ, tool(body, "gitleaks")):
            result = ss.scan_secrets(self.r)
        self.assertEqual((result["engine"], result["status"], result["findings"][0]["kind"]),
                         ("gitleaks", "findings", "github-pat"))
        self.assertFalse((self.r / ".sdd/security/gitleaks-report.json").exists())

    def test_requesting_a_missing_engine_is_an_error(self):
        write(self.r, ".sdd/config.json", json.dumps({"security": {"engine": "trufflehog"}}))
        self.assertEqual(ss.scan_secrets(self.r, engine="trufflehog")["status"], "error")


class Gate(Base):
    def layers(self, **kwargs):
        gate = security_gate(self.r, **kwargs)
        return gate, {entry["layer"]: entry["status"] for entry in gate["layers"]}

    def test_clean_repo_reports_missing_tools_as_not_run_never_as_clean(self):
        gate, by = self.layers()
        self.assertEqual(by, {"secrets": "clean", "code-scan": "NOT RUN", "dependencies": "NOT RUN", "pentest": "NOT RUN"})
        self.assertEqual(gate["exit"], 0)
        code, out = sdd(self.r, "security")
        self.assertEqual(code, 0)
        self.assertIn("NOT RUN: code-scan, dependencies", out)
        self.assertIn("unknown is not clean", out)

    def test_strict_mode_fails_when_an_enabled_layer_did_not_run(self):
        gate, _ = self.layers(strict=True)
        self.assertEqual((gate["exit"], gate["notRun"]), (3, ["code-scan", "dependencies"]))
        without(self.r, "code-scan", "dependencies")
        gate, by = self.layers(strict=True)
        self.assertEqual((gate["exit"], by["code-scan"], by["dependencies"]), (0, "off", "off"))
        self.assertIn("Switched off by the team", sdd(self.r, "security", "--strict")[1])

    def test_analysers_run_when_installed_and_their_exit_codes_are_read_correctly(self):
        write(self.r, ".sdd/codebase-profile.json", json.dumps({"languages": [{"name": "Python", "files": 3}]}))
        for body, expected, exit_code in (("exit 0", "clean", 0), ("echo 'B602 shell=True'; exit 1", "findings", 2),
                                          ("exit 9", "error", 1)):
            with mock.patch.dict(os.environ, tool(body, "bandit")):
                gate, by = self.layers()
            self.assertEqual((by["code-scan"], gate["exit"]), (expected, exit_code), body)
        with mock.patch.dict(os.environ, tool("echo 'B602 shell=True'; exit 1", "bandit")):
            self.assertIn("B602", sdd(self.r, "security")[1])

    def test_language_specific_tools_only_run_for_their_language(self):
        write(self.r, ".sdd/codebase-profile.json", json.dumps({"languages": [{"name": "Go", "files": 3}]}))
        with mock.patch.dict(os.environ, tool("exit 1", "bandit")):
            _, by = self.layers()
        self.assertEqual(by["code-scan"], "NOT RUN", "a Python analyser must not run on a Go project")

    def test_findings_outrank_everything_and_secret_files_are_flagged(self):
        git(self.r, "init", "-q")
        write(self.r, "a.py", f"x = '{GH}'\n")
        write(self.r, "server.key", "x")
        git(self.r, "add", "-f", "a.py", "server.key")
        gate, by = self.layers(strict=True)
        self.assertEqual((gate["exit"], by["secrets"]), (2, "findings"))
        kinds = [f["kind"] for f in gate["layers"][0]["findings"]]
        self.assertIn("secret-like file tracked by git", kinds)

    def test_regression_includes_the_gate(self):
        write(self.r, "a.py", f"x = '{GH}'\n")
        result = regression(self.r)
        self.assertFalse(result["ok"])
        self.assertEqual(next(x for x in result["results"] if x["label"] == "security: secrets")["status"], 1)
        (self.r / "a.py").unlink()
        self.assertTrue(regression(self.r)["ok"])
        self.assertFalse(regression(self.r, strict=True)["ok"], "strict: missing analysers fail the sweep")


class RedFirst(Base):
    def setUp(self):
        super().setUp()
        use_python_e2e(self.r)
        runner = write(self.r, "run-e2e.sh", '#!/bin/sh\n[ -f "$(dirname "$0")/app-works" ]\n')
        runner.chmod(0o755)
        cfg = json.loads((self.r / ".sdd/config.json").read_text())
        cfg["commands"]["e2e"] = "./run-e2e.sh"
        (self.r / ".sdd/config.json").write_text(json.dumps(cfg))
        feature(self.r, spec=SPEC, plan="# p", tasks="- [x] T-001 x (covers: REQ-001)")
        self.test_file = gen_tests(self.r, "f1")["file"]

    def test_red_then_green_with_unchanged_tests_is_proof(self):
        self.assertIn("no red run", proof_status(self.r, "f1")["problem"])
        self.assertTrue(any("red-first proof" in e for e in verify_feature(self.r, "f1", strict=True)["errors"]))
        self.assertTrue(prove(self.r, "f1", "red")["ok"])
        self.assertIn("no green run", proof_status(self.r, "f1")["problem"])
        self.assertFalse(prove(self.r, "f1", "green")["ok"], "still failing: nothing is recorded")
        write(self.r, "app-works", "")
        self.assertTrue(prove(self.r, "f1", "green")["ok"])
        self.assertIsNone(proof_status(self.r, "f1")["problem"])
        self.assertEqual(verify_feature(self.r, "f1", strict=True)["errors"], [])

    def test_a_red_run_that_passes_is_refused(self):
        write(self.r, "app-works", "")
        code, out = sdd(self.r, "prove", "red", "f1")
        self.assertEqual(code, 1)
        self.assertIn("NOT recorded", out)
        self.assertFalse((self.r / ".sdd/specs/f1/evidence.json").exists())

    def test_green_without_red_and_edited_tests_are_refused(self):
        with self.assertRaises(SecurityError):
            prove(self.r, "f1", "green")
        prove(self.r, "f1", "red")
        write(self.r, "app-works", "")
        with open(self.test_file, "a") as fh:
            fh.write("\n# weakened to pass\n")
        code, out = sdd(self.r, "prove", "green", "f1")
        self.assertEqual(code, 1)
        self.assertIn("changed since the red run", out)

    def test_editing_tests_after_proof_invalidates_it(self):
        prove(self.r, "f1", "red")
        write(self.r, "app-works", "")
        prove(self.r, "f1", "green")
        with open(self.test_file, "a") as fh:
            fh.write("\n# edited later\n")
        self.assertIn("changed after they were proven", proof_status(self.r, "f1")["problem"])
        feature(self.r, spec=SPEC.replace("approved", "shipped"))
        write(self.r, "tests/test_f1_unit.py", "# REQ-001")
        self.assertTrue(any("red-first proof" in e for e in verify_feature(self.r, "f1")["errors"]))

    def test_switch_off_and_parallel_hint(self):
        feature(self.r, tasks="- [ ] T-001 x (covers: REQ-001)")
        out = sdd(self.r, "next")[1]
        self.assertIn("in parallel (test track)", out)
        self.assertIn("sdd prove red f1", out)
        feature(self.r, tasks="- [x] T-001 x (covers: REQ-001)")
        without(self.r, "red-first")
        self.assertEqual(verify_feature(self.r, "f1", strict=True)["errors"], [])

    def test_no_generated_tests_means_nothing_to_prove(self):
        self.test_file.unlink()
        with self.assertRaises(SecurityError):
            prove(self.r, "f1", "red")
        self.assertIsNone(proof_status(self.r, "f1")["problem"])


if __name__ == "__main__":
    unittest.main()
