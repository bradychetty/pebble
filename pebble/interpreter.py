"""Tree-walking interpreter: executes the AST directly."""

import sys

from . import nodes
from .environment import Environment
from .errors import PebbleRuntimeError
from .stdlib import make_builtins
from .tokens import TokenType as T
from .values import (
    Builtin,
    PebbleFunction,
    is_number,
    is_truthy,
    stringify,
    type_name,
    values_equal,
)

MAX_CALL_DEPTH = 400


class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


class Interpreter:
    def __init__(self, out=None):
        self.out = out if out is not None else sys.stdout
        self.globals = Environment()
        self.env = self.globals
        self.depth = 0
        for name, builtin in make_builtins().items():
            self.globals.define(name, builtin)
        # Each Pebble call uses several Python frames, so Python's default
        # limit would trip well before MAX_CALL_DEPTH does.
        sys.setrecursionlimit(max(sys.getrecursionlimit(), 20000))

    def run(self, statements):
        for stmt in statements:
            self.execute(stmt)

    # -- statements -------------------------------------------------------

    def execute(self, stmt):
        match stmt:
            case nodes.ExprStmt(expression=e):
                self.evaluate(e)
            case nodes.Let(name=name, initializer=init):
                value = self.evaluate(init) if init is not None else None
                self.env.define(name.lexeme, value)
            case nodes.Print(expression=e):
                self.out.write(stringify(self.evaluate(e)) + "\n")
            case nodes.Block(statements=statements):
                self.execute_block(statements, Environment(self.env))
            case nodes.If(condition=c, then_branch=then, else_branch=other):
                if is_truthy(self.evaluate(c)):
                    self.execute(then)
                elif other is not None:
                    self.execute(other)
            case nodes.While(condition=c, body=body):
                self._while(c, body)
            case nodes.ForIn(var=var, iterable=it, body=body):
                self._for_in(var, it, body)
            case nodes.Return(value=v):
                raise ReturnSignal(self.evaluate(v) if v is not None else None)
            case nodes.Break():
                raise BreakSignal()
            case nodes.Continue():
                raise ContinueSignal()
            case nodes.FunctionDecl(name=name, params=params, body=body):
                fn = PebbleFunction(name.lexeme, [p.lexeme for p in params], body, self.env)
                self.env.define(name.lexeme, fn)
            case _:
                raise TypeError(f"unknown statement {stmt!r}")

    def execute_block(self, statements, env):
        previous = self.env
        self.env = env
        try:
            for stmt in statements:
                self.execute(stmt)
        finally:
            self.env = previous

    def _while(self, condition, body):
        while is_truthy(self.evaluate(condition)):
            try:
                self.execute(body)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def _for_in(self, var, iterable, body):
        sequence = self.evaluate(iterable)
        if not isinstance(sequence, (list, str)):
            raise PebbleRuntimeError(
                f"can only loop over a list or string, got {type_name(sequence)}",
                var.line, var.column,
            )
        # Iterate over a copy so pushing to the list inside the loop can't run forever.
        for item in list(sequence):
            # A fresh scope per iteration means closures capture that iteration's value.
            scope = Environment(self.env)
            scope.define(var.lexeme, item)
            try:
                self.execute_block([body], scope)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    # -- expressions ------------------------------------------------------

    def evaluate(self, expr):
        match expr:
            case nodes.Literal(value=v):
                return v
            case nodes.Variable(name=name):
                return self.env.get(name)
            case nodes.Assign():
                return self._assign(expr)
            case nodes.Unary(op=op, right=right):
                return self._unary(op, self.evaluate(right))
            case nodes.Binary(left=left, op=op, right=right):
                return self._binary(op, self.evaluate(left), self.evaluate(right))
            case nodes.Logical(left=left, op=op, right=right):
                # Short-circuit, and return the deciding operand rather than a bool.
                value = self.evaluate(left)
                if op.type == T.OR:
                    return value if is_truthy(value) else self.evaluate(right)
                return self.evaluate(right) if is_truthy(value) else value
            case nodes.Call(callee=callee, paren=paren, args=args):
                fn = self.evaluate(callee)
                return self.call(fn, [self.evaluate(a) for a in args], paren)
            case nodes.Index(obj=obj, bracket=bracket, index=index):
                container = self.evaluate(obj)
                position = self._check_index(container, self.evaluate(index), bracket)
                return container[position]
            case nodes.ListLiteral(elements=elements):
                return [self.evaluate(e) for e in elements]
            case nodes.Lambda(params=params, body=body):
                return PebbleFunction("lambda", [p.lexeme for p in params], body, self.env)
            case _:
                raise TypeError(f"unknown expression {expr!r}")

    def _assign(self, expr):
        target = expr.target
        if isinstance(target, nodes.Variable):
            value = self.evaluate(expr.value)
            self.env.assign(target.name, value)
            return value

        container = self.evaluate(target.obj)
        index = self.evaluate(target.index)
        value = self.evaluate(expr.value)
        if not isinstance(container, list):
            raise PebbleRuntimeError(
                f"cannot assign into a {type_name(container)} by index",
                target.bracket.line, target.bracket.column,
            )
        container[self._check_index(container, index, target.bracket)] = value
        return value

    def _check_index(self, container, index, bracket):
        if not isinstance(container, (list, str)):
            raise self._error(bracket, f"cannot index a {type_name(container)}")
        if not isinstance(index, int) or isinstance(index, bool):
            raise self._error(bracket, f"index must be an integer, got {type_name(index)}")
        if not -len(container) <= index < len(container):
            raise self._error(bracket, f"index {index} out of range for length {len(container)}")
        return index

    def _unary(self, op, right):
        if op.type == T.NOT:
            return not is_truthy(right)
        if not is_number(right):
            raise self._error(op, f"operand of '-' must be a number, got {type_name(right)}")
        return -right

    def _binary(self, op, left, right):
        kind = op.type

        if kind == T.EQUAL_EQUAL:
            return values_equal(left, right)
        if kind == T.NOT_EQUAL:
            return not values_equal(left, right)

        if kind == T.PLUS:
            if is_number(left) and is_number(right):
                return left + right
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            raise self._error(
                op,
                f"'+' needs two numbers or two strings, got {type_name(left)} and {type_name(right)}",
            )

        if kind in (T.LESS, T.LESS_EQUAL, T.GREATER, T.GREATER_EQUAL):
            both_numbers = is_number(left) and is_number(right)
            both_strings = isinstance(left, str) and isinstance(right, str)
            if not (both_numbers or both_strings):
                raise self._error(
                    op,
                    f"'{op.lexeme}' needs two numbers or two strings, "
                    f"got {type_name(left)} and {type_name(right)}",
                )
            if kind == T.LESS:
                return left < right
            if kind == T.LESS_EQUAL:
                return left <= right
            if kind == T.GREATER:
                return left > right
            return left >= right

        # Remaining operators are numeric only.
        if not (is_number(left) and is_number(right)):
            raise self._error(
                op,
                f"'{op.lexeme}' needs two numbers, got {type_name(left)} and {type_name(right)}",
            )
        if kind == T.MINUS:
            return left - right
        if kind == T.STAR:
            return left * right
        if right == 0:
            raise self._error(op, "division by zero" if kind == T.SLASH else "modulo by zero")
        if kind == T.PERCENT:
            return left % right
        # Division: stay exact for integers that divide evenly.
        if isinstance(left, int) and isinstance(right, int) and left % right == 0:
            return left // right
        return left / right

    # -- calls ------------------------------------------------------------

    def call(self, fn, args, paren):
        if isinstance(fn, PebbleFunction):
            low = high = fn.arity
        elif isinstance(fn, Builtin):
            low, high = fn.min_args, fn.max_args
        else:
            raise self._error(paren, f"can only call functions, got {type_name(fn)}")

        if not low <= len(args) <= high:
            expected = str(low) if low == high else f"{low} to {high}"
            raise self._error(paren, f"expected {expected} argument(s) but got {len(args)}")

        if isinstance(fn, Builtin):
            try:
                return fn.fn(args)
            except PebbleRuntimeError as err:
                if err.line is None:
                    err.line, err.column = paren.line, paren.column
                raise

        if self.depth >= MAX_CALL_DEPTH:
            raise self._error(paren, f"stack overflow (more than {MAX_CALL_DEPTH} nested calls)")

        env = Environment(fn.closure)
        for name, value in zip(fn.params, args):
            env.define(name, value)
        self.depth += 1
        try:
            self.execute_block(fn.body, env)
        except ReturnSignal as signal:
            return signal.value
        finally:
            self.depth -= 1
        return None

    @staticmethod
    def _error(token, message):
        return PebbleRuntimeError(message, token.line, token.column)
