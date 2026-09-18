import unittest

from pebble.errors import ParseError
from pebble.lexer import Lexer
from pebble.parser import Parser
from pebble.printer import dump


def parse(source):
    return Parser(Lexer(source).tokenize()).parse()


def tree(source):
    """Parse a program and dump every top-level statement, one per line."""
    return "\n".join(dump(s) for s in parse(source))


def expr(source):
    """Parse a single expression statement and dump just the expression."""
    (stmt,) = parse(source + ";")
    return dump(stmt.expression)


class ExpressionTests(unittest.TestCase):
    def test_literals(self):
        self.assertEqual(expr("1"), "1")
        self.assertEqual(expr("2.5"), "2.5")
        self.assertEqual(expr('"hi"'), '"hi"')
        self.assertEqual(expr("true"), "true")
        self.assertEqual(expr("nil"), "nil")

    def test_multiplication_binds_tighter_than_addition(self):
        self.assertEqual(expr("1 + 2 * 3"), "(+ 1 (* 2 3))")
        self.assertEqual(expr("1 * 2 + 3"), "(+ (* 1 2) 3)")

    def test_binary_operators_are_left_associative(self):
        self.assertEqual(expr("10 - 4 - 3"), "(- (- 10 4) 3)")
        self.assertEqual(expr("8 / 4 / 2"), "(/ (/ 8 4) 2)")

    def test_parentheses_override_precedence(self):
        self.assertEqual(expr("(1 + 2) * 3"), "(* (+ 1 2) 3)")

    def test_unary_minus(self):
        self.assertEqual(expr("-1 + 2"), "(+ (- 1) 2)")
        self.assertEqual(expr("--1"), "(- (- 1))")

    def test_comparison_and_equality_levels(self):
        self.assertEqual(expr("1 < 2 == true"), "(== (< 1 2) true)")

    def test_not_is_looser_than_comparison(self):
        self.assertEqual(expr("not a == b"), "(not (== a b))")

    def test_and_binds_tighter_than_or(self):
        self.assertEqual(expr("a or b and c"), "(or a (and b c))")

    def test_assignment_is_right_associative(self):
        self.assertEqual(expr("a = b = 3"), "(= a (= b 3))")

    def test_calls_and_indexing_chain(self):
        self.assertEqual(expr("f(1, 2)(3)"), "(call (call f 1 2) 3)")
        self.assertEqual(expr("xs[0][1]"), "(index (index xs 0) 1)")
        self.assertEqual(expr("f(x)[2]"), "(index (call f x) 2)")

    def test_list_literals(self):
        self.assertEqual(expr("[]"), "(list)")
        self.assertEqual(expr("[1, 2 + 3]"), "(list 1 (+ 2 3))")

    def test_index_assignment(self):
        self.assertEqual(expr("xs[1] = 9"), "(= (index xs 1) 9)")

    def test_lambda_expression(self):
        self.assertEqual(expr("fn(a, b) { return a; }"), "(fn (a b) (return a))")


class StatementTests(unittest.TestCase):
    def test_let_with_and_without_initializer(self):
        self.assertEqual(tree("let x = 1;"), "(let x 1)")
        self.assertEqual(tree("let x;"), "(let x)")

    def test_print(self):
        self.assertEqual(tree("print 1 + 2;"), "(print (+ 1 2))")

    def test_if_else_chain(self):
        src = "if a { print 1; } else if b { print 2; } else { print 3; }"
        self.assertEqual(
            tree(src),
            "(if a (block (print 1)) (if b (block (print 2)) (block (print 3))))",
        )

    def test_while_and_for(self):
        self.assertEqual(
            tree("while x < 3 { x = x + 1; }"),
            "(while (< x 3) (block (expr (= x (+ x 1)))))",
        )
        self.assertEqual(
            tree("for i in xs { print i; }"),
            "(for i xs (block (print i)))",
        )

    def test_function_declaration(self):
        self.assertEqual(
            tree("fn add(a, b) { return a + b; }"),
            "(fn add (a b) (return (+ a b)))",
        )

    def test_bare_return(self):
        self.assertEqual(tree("fn f() { return; }"), "(fn f () (return))")

    def test_break_and_continue_inside_loop(self):
        self.assertEqual(
            tree("while true { break; continue; }"),
            "(while true (block (break) (continue)))",
        )

    def test_nested_block(self):
        self.assertEqual(tree("{ let a = 1; }"), "(block (let a 1))")

    def test_fn_at_statement_start_without_name_is_an_expression(self):
        self.assertEqual(tree("fn(x) { return x; }(1);"), "(expr (call (fn (x) (return x)) 1))")


class ErrorTests(unittest.TestCase):
    def assertParseError(self, source, pattern):
        with self.assertRaisesRegex(ParseError, pattern):
            parse(source)

    def test_missing_semicolon(self):
        self.assertParseError("print 1", r"expected ';' after value, found end of file")

    def test_missing_expression(self):
        self.assertParseError("let x = ;", "expected expression")

    def test_unclosed_paren(self):
        self.assertParseError("(1 + 2;", r"expected '\)' after expression")

    def test_unclosed_block(self):
        self.assertParseError("if true { print 1;", r"expected '}' after block")

    def test_if_requires_braces(self):
        self.assertParseError("if true print 1;", r"expected '\{' after if condition")

    def test_invalid_assignment_target(self):
        self.assertParseError("1 + 2 = 3;", "invalid assignment target")
        self.assertParseError("f() = 3;", "invalid assignment target")

    def test_return_outside_function(self):
        self.assertParseError("return 1;", "'return' outside of a function")

    def test_break_outside_loop(self):
        self.assertParseError("break;", "'break' outside of a loop")

    def test_break_does_not_cross_function_boundary(self):
        self.assertParseError("while true { fn f() { break; } }", "'break' outside of a loop")

    def test_duplicate_parameter(self):
        self.assertParseError("fn f(a, a) { }", "duplicate parameter 'a'")

    def test_error_reports_position(self):
        with self.assertRaises(ParseError) as ctx:
            parse("let a = 1;\nlet = 2;")
        self.assertEqual((ctx.exception.line, ctx.exception.column), (2, 5))


if __name__ == "__main__":
    unittest.main()
