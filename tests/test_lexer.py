import unittest

from pebble.errors import LexError
from pebble.lexer import Lexer
from pebble.tokens import TokenType as T


def lex(source):
    return Lexer(source).tokenize()


def types(source):
    return [t.type for t in lex(source)]


class LexerTests(unittest.TestCase):
    def test_empty_source_gives_only_eof(self):
        self.assertEqual(types(""), [T.EOF])

    def test_punctuation_and_operators(self):
        self.assertEqual(
            types("( ) { } [ ] , ; + - * / %"),
            [T.LEFT_PAREN, T.RIGHT_PAREN, T.LEFT_BRACE, T.RIGHT_BRACE,
             T.LEFT_BRACKET, T.RIGHT_BRACKET, T.COMMA, T.SEMICOLON,
             T.PLUS, T.MINUS, T.STAR, T.SLASH, T.PERCENT, T.EOF],
        )

    def test_one_and_two_character_comparisons(self):
        self.assertEqual(
            types("= == != < <= > >="),
            [T.EQUAL, T.EQUAL_EQUAL, T.NOT_EQUAL, T.LESS, T.LESS_EQUAL,
             T.GREATER, T.GREATER_EQUAL, T.EOF],
        )

    def test_integer_and_float_literals(self):
        tokens = lex("42 3.14 0")
        self.assertEqual([t.literal for t in tokens[:3]], [42, 3.14, 0])
        self.assertIsInstance(tokens[0].literal, int)
        self.assertIsInstance(tokens[1].literal, float)

    def test_trailing_dot_is_not_part_of_number(self):
        # "1." lexes the number 1, then fails on the stray '.'
        with self.assertRaisesRegex(LexError, r"unexpected character '\.'"):
            lex("1.")

    def test_keywords_versus_identifiers(self):
        self.assertEqual(
            types("let letter fn fnord nil"),
            [T.LET, T.IDENTIFIER, T.FN, T.IDENTIFIER, T.NIL, T.EOF],
        )

    def test_identifiers_can_contain_digits_and_underscores(self):
        token = lex("_x1_y2")[0]
        self.assertEqual((token.type, token.lexeme), (T.IDENTIFIER, "_x1_y2"))

    def test_string_literal_and_escapes(self):
        token = lex(r'"a\tb\n\"c\"\\"')[0]
        self.assertEqual(token.type, T.STRING)
        self.assertEqual(token.literal, 'a\tb\n"c"\\')

    def test_comments_are_skipped(self):
        self.assertEqual(types("1 # ignore this\n2"), [T.NUMBER, T.NUMBER, T.EOF])

    def test_line_and_column_tracking(self):
        tokens = lex("let x\n  = 5;")
        positions = [(t.lexeme, t.line, t.column) for t in tokens[:-1]]
        self.assertEqual(
            positions,
            [("let", 1, 1), ("x", 1, 5), ("=", 2, 3), ("5", 2, 5), (";", 2, 6)],
        )

    def test_unterminated_string(self):
        with self.assertRaisesRegex(LexError, "unterminated string"):
            lex('"abc')

    def test_string_cannot_span_lines(self):
        with self.assertRaisesRegex(LexError, "unterminated string"):
            lex('"abc\ndef"')

    def test_invalid_escape(self):
        with self.assertRaisesRegex(LexError, "invalid escape"):
            lex(r'"\q"')

    def test_lone_bang_suggests_not(self):
        with self.assertRaisesRegex(LexError, "not"):
            lex("!x")

    def test_unexpected_character_reports_position(self):
        with self.assertRaises(LexError) as ctx:
            lex("let x = 1;\n  @")
        self.assertEqual((ctx.exception.line, ctx.exception.column), (2, 3))


if __name__ == "__main__":
    unittest.main()
