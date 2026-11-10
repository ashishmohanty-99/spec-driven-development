"""Security regression tests: each one pins a specific attack that must stay blocked."""
import os
import unittest
from unittest import mock

from specpilot import pentest as pt
from specpilot.audit import audit
from specpilot.gentests import gen_tests
from specpilot.security import SecurityError, redact, safe_join, scan_text_for_secrets, validate_feature, write_text
from specpilot.spec import verify_feature

from .helpers import feature, sdd, tmp, write

FAKE_KEY = "sk-" + "A1b2C3d4" * 4  # test fixture, not a real credential


class PathTests(unittest.TestCase):
    def test_feature_names_cannot_traverse(self):
        for bad in ("../x", "a/b", "..", "A", "a b", "", "x" * 65, "-x", "a\nb", "a;rm"):
            with self.assertRaises(SecurityError, msg=bad):
                validate_feature(bad)

    def test_cli_rejects_traversal_everywhere(self):
        r = tmp()
        sdd(r, "init")
        for cmd in ("new", "gen-tests", "verify"):
            code, _ = sdd(r, cmd, "../../etc")
            self.assertEqual(code, 1, cmd)
        self.assertFalse((r.parent / "etc").exists())

    def test_safe_join_and_symlink_writes(self):
        r = tmp()
        with self.assertRaises(SecurityError):
            safe_join(r, "../outside")
        outside = tmp()
        os.symlink(outside, r / "link")
        with self.assertRaises(SecurityError):
            write_text(r, r / "link" / "pwned.txt", "x")
        self.assertFalse((outside / "pwned.txt").exists())

    def test_init_does_not_write_through_symlinked_instruction_file(self):
        r, outside = tmp(), tmp()
        target = write(outside, "victim.md", "original")
        os.symlink(target, r / "CLAUDE.md")
        code, _ = sdd(r, "init")
        self.assertEqual(code, 1)
        self.assertEqual(target.read_text(), "original")

    def test_config_cannot_redirect_outside_root(self):
        r = tmp()
        sdd(r, "init")
        write(r, ".sdd/config.json", '{"specsDir": "../../outside", "e2eDir": "/tmp/evil"}')
        self.assertEqual(sdd(r, "new", "f1")[0], 1)
        self.assertEqual(sdd(r, "status")[0], 1)


class InjectionTests(unittest.TestCase):
    def test_spec_text_cannot_become_code(self):
        r = tmp()
        sdd(r, "init")
        evil = '''x"); import os; os.system("touch /tmp/pwned"); ("'''
        feature(r, spec=f"Status: approved\n- REQ-001: a\n- REQ-001 — Given {evil}, when '''b''', then c\\")
        out = gen_tests(r, "f1")["file"]
        source = out.read_text()
        compile(source, str(out), "exec")  # still valid Python
        import ast
        calls = [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Call)]
        names = {getattr(c.func, "id", getattr(c.func, "attr", "")) for c in calls}
        self.assertLessEqual(names, {"run_scenario", "missing", "requirement"})

    def test_pentest_arguments_cannot_inject_options(self):
        r = tmp()
        for bad in ("--config=/etc/passwd", "-n", "a\nb", "ftp://x", "https://user:pw@host.example"):
            with self.assertRaises(SecurityError, msg=bad):
                pt.validate_target(r, bad, ["host.example"])
        with self.assertRaises(SecurityError):
            pt.validate_target(r, "../../etc", [])
        with self.assertRaises(SecurityError):
            pt.build_args(["."], diff_base="--exec=evil")
        with self.assertRaises(SecurityError):
            pt.build_args(["."], scan_mode="quick --mcp-server x")
        args = pt.build_args(["."], instruction="--resume x\n--config y")
        self.assertTrue(all(a.startswith("--") and "\n" not in a for a in args))
        self.assertIn("--instruction=--resume x --config y", args)


class PentestGuardTests(unittest.TestCase):
    def setUp(self):
        self.r = tmp()
        sdd(self.r, "init")

    def test_url_must_be_allow_listed_by_config(self):
        with self.assertRaises(SecurityError):
            pt.validate_target(self.r, "https://victim.example", [])
        self.assertEqual(pt.validate_target(self.r, "https://staging.example/x", ["staging.example"]),
                         "https://staging.example/x")
        self.assertTrue(pt.validate_target(self.r, "http://localhost:3000", []))

    def test_not_run_is_exit_3_never_0(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            for args in (["pentest"], ["pentest", "--target", "."],
                         ["pentest", "--target", ".", "--authorized"],
                         ["pentest", "--target", "https://victim.example", "--authorized"]):
                code, out = sdd(self.r, *args)
                self.assertEqual(code, 3, args)
                self.assertIn("NOT RUN", out)

    def test_there_is_no_way_to_pass_a_key_on_the_command_line(self):
        code, _ = sdd(self.r, "pentest", "--target", ".", "--api-key", FAKE_KEY)
        self.assertEqual(code, 2)

    def test_model_env_rules(self):
        self.assertIsNotNone(pt.check_model_env({}))
        self.assertIsNotNone(pt.check_model_env({"STRIX_LLM": "openai/gpt"}))
        self.assertIsNone(pt.check_model_env({"STRIX_LLM": "ollama/qwen3-vl", "LLM_API_BASE": "http://localhost:11434"}))
        self.assertIsNone(pt.check_model_env({"STRIX_LLM": "openai/gpt", "LLM_API_KEY": FAKE_KEY}))
        self.assertIn("plain http", pt.check_model_env(
            {"STRIX_LLM": "x/y", "LLM_API_KEY": FAKE_KEY, "LLM_API_BASE": "http://gw.example/v1"}))
        self.assertIn("credentials", pt.check_model_env(
            {"STRIX_LLM": "x/y", "LLM_API_KEY": FAKE_KEY, "LLM_API_BASE": "https://u:p@gw.example"}))

    def test_real_run_redacts_key_and_limits_environment(self):
        """Run against a stand-in `strix` that prints its environment, to prove what a scan can see."""
        bindir = tmp()
        fake = write(bindir, "strix", "#!/bin/sh\necho \"key=$LLM_API_KEY other=$AWS_SECRET_ACCESS_KEY args=$*\"\nexit 2\n")
        fake.chmod(0o755)
        env = {"PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}", "STRIX_LLM": "openai/gpt",
               "LLM_API_KEY": FAKE_KEY, "AWS_SECRET_ACCESS_KEY": "do-not-forward-this"}
        lines = []
        with mock.patch.dict(os.environ, env, clear=True):
            result = pt.pentest(self.r, ["."], authorized=True, out=lines.append)
        output = "\n".join(lines)
        self.assertTrue(result["ran"])
        self.assertEqual(result["status"], 2)
        self.assertNotIn(FAKE_KEY, output)
        self.assertIn("REDACTED", output)
        self.assertNotIn("do-not-forward-this", output)
        self.assertIn("--non-interactive", output)
        record = (self.r / result["record"]).read_text()
        self.assertNotIn(FAKE_KEY, record)
        self.assertIn('"result": "findings"', record)


class SecretTests(unittest.TestCase):
    def test_detection_and_redaction(self):
        self.assertTrue(scan_text_for_secrets(f"LLM_API_KEY={FAKE_KEY}"))
        self.assertTrue(scan_text_for_secrets("-----BEGIN RSA PRIVATE KEY-----"))
        self.assertEqual(scan_text_for_secrets('api_key = os.environ["X"]\npassword: <your password>'), [])
        self.assertNotIn(FAKE_KEY, redact(f"token {FAKE_KEY} end", {}))

    def test_verify_and_audit_fail_on_committed_secret(self):
        r = tmp()
        sdd(r, "init")
        feature(r, spec=f"Status: draft\n- REQ-001: a\nuse key {FAKE_KEY}")
        v = verify_feature(r, "f1")
        self.assertTrue(any("SECURITY" in e for e in v["errors"]))
        self.assertFalse(any(FAKE_KEY in e for e in v["errors"]))
        code, out = sdd(r, "audit")
        self.assertEqual(code, 1)
        self.assertNotIn(FAKE_KEY, out)

    def test_audit_clean_after_init_and_flags_bad_config_and_ci(self):
        r = tmp()
        sdd(r, "init")
        self.assertTrue(audit(r)["ok"])
        write(r, ".sdd/config.json", '{"pentest": {"apiKey": "x"}}')
        write(r, ".github/workflows/x.yml", "on: pull_request_target\nenv:\n  K: ${{ secrets.LLM_API_KEY }}")
        messages = "\n".join(m for _, m in audit(r)["findings"])
        self.assertIn("config.json mentions a credential", messages)
        self.assertIn("pull_request_target", messages)


if __name__ == "__main__":
    unittest.main()
