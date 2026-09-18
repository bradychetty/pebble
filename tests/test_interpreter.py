import io
import unittest

from pebble.errors import PebbleRuntimeError
from pebble.interpreter import Interpreter
from pebble.lexer import Lexer
from pebble.parser import Parser


def run(source):
    """Run a program and return everything it printed."""
    out = io.StringIO()
    Interpreter(out).run(Parser(Lexer(source).tokenize()).parse())
    return out.getvalue()


def lines(source):
    return run(source).splitlines()


class ArithmeticTests(unittest.TestCase):
    def test_basic_operators_and_precedence(self):
        self.assertEqual(lines("print 1 + 2 * 3; print (1 + 2) * 3; print 10 - 4 - 3;"), ["7", "9", "3"])

    def test_division_is_exact_when_it_can_be(self):
        self.assertEqual(lines("print 8 / 2; print 7 / 2; print 1 / 4;"), ["4", "3.5", "0.25"])

    def test_large_integers_stay_exact(self):
        self.assertEqual(run("print 10000000000000000 / 2;"), "5000000000000000\n")

    def test_modulo(self):
        self.assertEqual(lines("print 10 % 3; print 7.5 % 2;"), ["1", "1.5"])

    def test_unary_minus(self):
        self.assertEqual(lines("print -3; print - -3; print 2 - -3;"), ["-3", "3", "5"])

    def test_float_that_is_whole_prints_without_decimal(self):
        self.assertEqual(run("print 2.0 * 3;"), "6\n")

    def test_division_by_zero(self):
        with self.assertRaisesRegex(PebbleRuntimeError, "division by zero"):
            run("print 1 / 0;")
        with self.assertRaisesRegex(PebbleRuntimeError, "modulo by zero"):
            run("print 1 % 0;")


class ValueTests(unittest.TestCase):
    def test_print_forms(self):
        self.assertEqual(lines('print nil; print true; print "hi"; print [1, "a", nil];'),
                         ["nil", "true", "hi", '[1, "a", nil]'])

    def test_string_concatenation(self):
        self.assertEqual(run('print "ab" + "cd";'), "abcd\n")

    def test_plus_rejects_mixed_types(self):
        with self.assertRaisesRegex(PebbleRuntimeError, "'\\+' needs two numbers or two strings"):
            run('print 1 + "a";')

    def test_equality_does_not_confuse_bools_and_numbers(self):
        self.assertEqual(lines("print 1 == true; print 0 == false; print true == true; print 1 == 1.0;"),
                         ["false", "false", "true", "true"])

    def test_equality_across_types_and_lists(self):
        self.assertEqual(lines('print nil == false; print "1" == 1; print [1, [2]] == [1, [2]]; print [1] == [2];'),
                         ["false", "false", "true", "false"])

    def test_comparisons(self):
        self.assertEqual(lines('print 1 < 2; print 2 <= 2; print "a" < "b"; print 3 > 4;'),
                         ["true", "true", "true", "false"])

    def test_comparing_mixed_types_is_an_error(self):
        with self.assertRaisesRegex(PebbleRuntimeError, "needs two numbers or two strings"):
            run('print 1 < "a";')

    def test_truthiness_only_nil_and_false_are_falsy(self):
        src = 'if 0 { print "zero"; } if "" { print "empty"; } if nil { print "nil"; } if false { print "f"; }'
        self.assertEqual(lines(src), ["zero", "empty"])

    def test_not(self):
        self.assertEqual(lines("print not true; print not nil; print not 0;"), ["false", "true", "false"])

    def test_and_or_return_operands_and_short_circuit(self):
        src = """
        print nil or "default";
        print 1 and 2;
        print false and boom();
        print true or boom();
        """
        self.assertEqual(lines(src), ["default", "2", "false", "true"])


class VariableTests(unittest.TestCase):
    def test_let_and_assignment(self):
        self.assertEqual(lines("let x = 1; x = x + 1; print x;"), ["2"])

    def test_let_without_initializer_is_nil(self):
        self.assertEqual(run("let x; print x;"), "nil\n")

    def test_assignment_is_an_expression(self):
        self.assertEqual(lines("let a; let b; a = b = 3; print a + b;"), ["6"])

    def test_undefined_variable(self):
        with self.assertRaisesRegex(PebbleRuntimeError, "undefined variable 'nope'"):
            run("print nope;")

    def test_assigning_to_undeclared_variable_is_an_error(self):
        with self.assertRaisesRegex(PebbleRuntimeError, "undefined variable 'x'"):
            run("x = 1;")

    def test_block_scope_shadows_and_restores(self):
        src = "let x = 1; { let x = 2; print x; } print x;"
        self.assertEqual(lines(src), ["2", "1"])

    def test_block_can_assign_outer_variable(self):
        self.assertEqual(run("let x = 1; { x = 5; } print x;"), "5\n")

    def test_scope_is_restored_after_an_error_in_a_block(self):
        out = io.StringIO()
        interp = Interpreter(out)
        with self.assertRaises(PebbleRuntimeError):
            interp.run(Parser(Lexer("{ let inner = 1; print missing; }").tokenize()).parse())
        self.assertIs(interp.env, interp.globals)


class ControlFlowTests(unittest.TestCase):
    def test_if_else_if_else(self):
        src = """
        fn grade(n) {
            if n >= 90 { return "A"; }
            else if n >= 80 { return "B"; }
            else { return "C"; }
        }
        print grade(95); print grade(85); print grade(10);
        """
        self.assertEqual(lines(src), ["A", "B", "C"])

    def test_while_loop(self):
        self.assertEqual(lines("let i = 0; while i < 3 { print i; i = i + 1; }"), ["0", "1", "2"])

    def test_for_over_list_and_string(self):
        self.assertEqual(lines("for x in [1, 2] { print x * 10; }"), ["10", "20"])
        self.assertEqual(lines('for c in "ab" { print c; }'), ["a", "b"])

    def test_for_over_range(self):
        self.assertEqual(lines("for i in range(1, 4) { print i; }"), ["1", "2", "3"])

    def test_break_and_continue(self):
        src = """
        for i in range(10) {
            if i == 2 { continue; }
            if i == 5 { break; }
            print i;
        }
        """
        self.assertEqual(lines(src), ["0", "1", "3", "4"])

    def test_break_only_exits_inner_loop(self):
        src = """
        for i in range(2) {
            for j in range(5) { if j == 1 { break; } print i * 10 + j; }
        }
        """
        self.assertEqual(lines(src), ["0", "10"])

    def test_pushing_during_iteration_does_not_loop_forever(self):
        self.assertEqual(lines("let xs = [1]; for x in xs { push(xs, x); } print len(xs);"), ["2"])

    def test_for_needs_a_list_or_string(self):
        with self.assertRaisesRegex(PebbleRuntimeError, "can only loop over a list or string"):
            run("for x in 5 { }")


class FunctionTests(unittest.TestCase):
    def test_call_and_return(self):
        self.assertEqual(run("fn add(a, b) { return a + b; } print add(2, 3);"), "5\n")

    def test_function_without_return_gives_nil(self):
        self.assertEqual(run("fn f() { } print f();"), "nil\n")

    def test_bare_return_gives_nil(self):
        self.assertEqual(run("fn f() { return; print 1; } print f();"), "nil\n")

    def test_recursion(self):
        src = "fn fact(n) { if n <= 1 { return 1; } return n * fact(n - 1); } print fact(10);"
        self.assertEqual(run(src), "3628800\n")

    def test_return_from_inside_nested_loops(self):
        src = """
        fn find(xs, target) {
            for i in range(len(xs)) { if xs[i] == target { return i; } }
            return -1;
        }
        print find([5, 6, 7], 7); print find([5, 6, 7], 9);
        """
        self.assertEqual(lines(src), ["2", "-1"])

    def test_closures_keep_their_own_state(self):
        src = """
        fn counter() { let n = 0; return fn() { n = n + 1; return n; }; }
        let a = counter(); let b = counter();
        a(); a();
        print a(); print b();
        """
        self.assertEqual(lines(src), ["3", "1"])

    def test_closure_captures_loop_variable_per_iteration(self):
        src = """
        let fns = [];
        for i in range(3) { push(fns, fn() { return i; }); }
        for f in fns { print f(); }
        """
        self.assertEqual(lines(src), ["0", "1", "2"])

    def test_functions_are_values(self):
        src = """
        fn twice(f, x) { return f(f(x)); }
        print twice(fn(n) { return n * 3; }, 2);
        """
        self.assertEqual(run(src), "18\n")

    def test_immediately_invoked_lambda(self):
        self.assertEqual(run("print fn(x) { return x + 1; }(4);"), "5\n")

    def test_mutual_recursion_through_globals(self):
        src = """
        fn is_even(n) { if n == 0 { return true; } return is_odd(n - 1); }
        fn is_odd(n) { if n == 0 { return false; } return is_even(n - 1); }
        print is_even(10); print is_odd(7);
        """
        self.assertEqual(lines(src), ["true", "true"])

    def test_function_printing(self):
        self.assertEqual(lines("fn f() { } print f; print len;"), ["<fn f>", "<builtin len>"])

    def test_wrong_argument_count(self):
        with self.assertRaisesRegex(PebbleRuntimeError, r"expected 2 argument\(s\) but got 1"):
            run("fn f(a, b) { } f(1);")

    def test_calling_a_non_function(self):
        with self.assertRaisesRegex(PebbleRuntimeError, "can only call functions, got number"):
            run("let x = 3; x();")

    def test_runaway_recursion_is_a_clean_error(self):
        with self.assertRaisesRegex(PebbleRuntimeError, "stack overflow"):
            run("fn f(n) { return f(n + 1); } f(0);")

    def test_depth_counter_recovers_after_an_error(self):
        interp = Interpreter(io.StringIO())
        program = Parser(Lexer("fn f() { return f(); } f();").tokenize()).parse()
        with self.assertRaises(PebbleRuntimeError):
            interp.run(program)
        self.assertEqual(interp.depth, 0)


class ListTests(unittest.TestCase):
    def test_index_read_and_negative_index(self):
        self.assertEqual(lines("let xs = [10, 20, 30]; print xs[0]; print xs[-1];"), ["10", "30"])

    def test_index_write(self):
        self.assertEqual(run("let xs = [1, 2]; xs[1] = 9; print xs;"), "[1, 9]\n")

    def test_string_indexing(self):
        self.assertEqual(run('print "hello"[1];'), "e\n")

    def test_lists_are_shared_by_reference(self):
        self.assertEqual(run("let a = [1]; let b = a; push(b, 2); print a;"), "[1, 2]\n")

    def test_index_out_of_range(self):
        with self.assertRaisesRegex(PebbleRuntimeError, "index 3 out of range for length 3"):
            run("let xs = [1, 2, 3]; print xs[3];")

    def test_index_must_be_integer(self):
        with self.assertRaisesRegex(PebbleRuntimeError, "index must be an integer"):
            run('let xs = [1]; print xs["a"];')
        with self.assertRaisesRegex(PebbleRuntimeError, "index must be an integer"):
            run("let xs = [1]; print xs[0.5];")

    def test_cannot_index_a_number(self):
        with self.assertRaisesRegex(PebbleRuntimeError, "cannot index a number"):
            run("let x = 1; print x[0];")

    def test_strings_are_immutable(self):
        with self.assertRaisesRegex(PebbleRuntimeError, "cannot assign into a string"):
            run('let s = "abc"; s[0] = "x";')

    def test_self_referencing_list_prints_without_recursing_forever(self):
        self.assertEqual(run("let xs = [1]; push(xs, xs); print xs;"), "[1, [...]]\n")


class BuiltinTests(unittest.TestCase):
    def test_len(self):
        self.assertEqual(lines('print len([1, 2]); print len("abc"); print len([]);'), ["2", "3", "0"])

    def test_len_rejects_numbers(self):
        with self.assertRaisesRegex(PebbleRuntimeError, "len\\(\\) expects a list or string, got number"):
            run("len(5);")

    def test_push_and_pop(self):
        self.assertEqual(lines("let xs = []; push(xs, 1); push(xs, 2); print pop(xs); print xs;"),
                         ["2", "[1]"])

    def test_pop_from_empty_list(self):
        with self.assertRaisesRegex(PebbleRuntimeError, "pop\\(\\) from an empty list"):
            run("pop([]);")

    def test_str(self):
        self.assertEqual(run('print "n=" + str(42);'), "n=42\n")
        self.assertEqual(run("print str([1, 2]);"), "[1, 2]\n")

    def test_num(self):
        self.assertEqual(lines('print num("42") + 1; print num("2.5"); print num(" 7 ");'), ["43", "2.5", "7"])

    def test_num_rejects_garbage(self):
        with self.assertRaisesRegex(PebbleRuntimeError, 'cannot convert "abc" to a number'):
            run('num("abc");')
        with self.assertRaisesRegex(PebbleRuntimeError, "cannot convert"):
            run('num("1_000");')

    def test_type(self):
        src = 'print type(1); print type("s"); print type(nil); print type(true); print type([]); print type(len);'
        self.assertEqual(lines(src), ["number", "string", "nil", "bool", "list", "function"])

    def test_range_forms(self):
        self.assertEqual(lines("print range(3); print range(2, 5); print range(10, 0, -4);"),
                         ["[0, 1, 2]", "[2, 3, 4]", "[10, 6, 2]"])

    def test_range_step_zero(self):
        with self.assertRaisesRegex(PebbleRuntimeError, "step cannot be zero"):
            run("range(0, 5, 0);")

    def test_builtin_errors_point_at_the_call(self):
        with self.assertRaises(PebbleRuntimeError) as ctx:
            run("let a = 1;\n  len(5);")
        self.assertEqual(ctx.exception.line, 2)

    def test_builtin_argument_count(self):
        with self.assertRaisesRegex(PebbleRuntimeError, r"expected 1 argument\(s\) but got 2"):
            run("len(1, 2);")
        with self.assertRaisesRegex(PebbleRuntimeError, r"expected 1 to 3 argument\(s\) but got 0"):
            run("range();")


class ErrorPositionTests(unittest.TestCase):
    def test_runtime_error_reports_line_and_column_of_operator(self):
        with self.assertRaises(PebbleRuntimeError) as ctx:
            run('let a = 1;\nprint a + "x";')
        self.assertEqual((ctx.exception.line, ctx.exception.column), (2, 9))

    def test_error_string_format(self):
        with self.assertRaises(PebbleRuntimeError) as ctx:
            run("print missing;")
        self.assertEqual(str(ctx.exception), "[line 1, col 7] Runtime error: undefined variable 'missing'")


if __name__ == "__main__":
    unittest.main()
