import io
import unittest
from pathlib import Path

from pebble.interpreter import Interpreter
from pebble.lexer import Lexer
from pebble.parser import Parser

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


class ExampleTests(unittest.TestCase):
    """Every examples/*.pb program must print exactly what its .expected file says."""

    def test_examples_match_expected_output(self):
        programs = sorted(EXAMPLES.glob("*.pb"))
        self.assertTrue(programs, "no example programs found")
        for program in programs:
            with self.subTest(program=program.name):
                out = io.StringIO()
                source = program.read_text(encoding="utf-8")
                Interpreter(out).run(Parser(Lexer(source).tokenize()).parse())
                expected = program.with_suffix(".expected").read_text(encoding="utf-8")
                self.assertEqual(out.getvalue(), expected)


if __name__ == "__main__":
    unittest.main()
