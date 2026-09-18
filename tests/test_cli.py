import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def pebble(*args, stdin=None):
    return subprocess.run(
        [sys.executable, "-m", "pebble", *args],
        cwd=ROOT, input=stdin, capture_output=True, text=True, timeout=30,
    )


class CliTests(unittest.TestCase):
    def script(self, source):
        f = tempfile.NamedTemporaryFile("w", suffix=".pb", delete=False, encoding="utf-8")
        self.addCleanup(Path(f.name).unlink)
        f.write(source)
        f.close()
        return f.name

    def test_runs_a_file(self):
        result = pebble(self.script('print "ok";'))
        self.assertEqual((result.returncode, result.stdout), (0, "ok\n"))

    def test_syntax_error_exit_code_and_message(self):
        result = pebble(self.script("print 1"))
        self.assertEqual(result.returncode, 65)
        self.assertIn("Syntax error", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_runtime_error_exit_code_and_message(self):
        result = pebble(self.script("print 1 / 0;"))
        self.assertEqual(result.returncode, 70)
        self.assertIn("division by zero", result.stderr)

    def test_output_before_a_runtime_error_is_kept(self):
        result = pebble(self.script('print "before"; print nope;'))
        self.assertEqual(result.stdout, "before\n")
        self.assertEqual(result.returncode, 70)

    def test_missing_file(self):
        result = pebble("does-not-exist.pb")
        self.assertEqual(result.returncode, 1)
        self.assertIn("cannot read", result.stderr)

    def test_ast_flag(self):
        result = pebble("--ast", self.script("print 1 + 2 * 3;"))
        self.assertEqual(result.stdout, "(print (+ 1 (* 2 3)))\n")

    def test_tokens_flag(self):
        result = pebble("--tokens", self.script("let x;"))
        self.assertIn("LET", result.stdout)
        self.assertIn("EOF", result.stdout)

    def test_repl_evaluates_expressions_and_keeps_state(self):
        result = pebble(stdin="let x = 4\nx * 2\nfn f(n) {\nreturn n + 1;\n}\nf(x)\n")
        self.assertEqual(result.returncode, 0)
        self.assertIn("8\n", result.stdout)
        self.assertIn("5\n", result.stdout)

    def test_repl_survives_errors(self):
        result = pebble(stdin="1 / 0\nprint 2\n")
        self.assertIn("division by zero", result.stdout)
        self.assertIn("2\n", result.stdout)


if __name__ == "__main__":
    unittest.main()
