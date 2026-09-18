"""Recursive-descent parser: tokens in, list of statements out.

Expression precedence, loosest to tightest:

    assignment   =                  (right associative)
    or
    and
    not
    equality     == !=
    comparison   < <= > >=
    term         + -
    factor       * / %
    unary        -
    postfix      f(...)  xs[i]
"""

from . import nodes
from .errors import ParseError
from .tokens import Token, TokenType as T


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.loop_depth = 0
        self.fn_depth = 0

    def parse(self):
        statements = []
        while not self._at_end():
            statements.append(self._statement())
        return statements

    # -- statements -------------------------------------------------------

    def _statement(self):
        if self._check(T.FN) and self._peek_next().type == T.IDENTIFIER:
            self._advance()
            return self._function_decl()
        if self._match(T.LET):
            return self._let()
        if self._match(T.PRINT):
            value = self._expression()
            self._consume(T.SEMICOLON, "expected ';' after value")
            return nodes.Print(value)
        if self._match(T.IF):
            return self._if()
        if self._match(T.WHILE):
            return self._while()
        if self._match(T.FOR):
            return self._for()
        if self._match(T.RETURN):
            return self._return()
        if self._match(T.BREAK):
            return self._loop_jump(nodes.Break, "break")
        if self._match(T.CONTINUE):
            return self._loop_jump(nodes.Continue, "continue")
        if self._match(T.LEFT_BRACE):
            return nodes.Block(self._block())
        return self._expression_statement()

    def _let(self):
        name = self._consume(T.IDENTIFIER, "expected variable name after 'let'")
        initializer = self._expression() if self._match(T.EQUAL) else None
        self._consume(T.SEMICOLON, "expected ';' after variable declaration")
        return nodes.Let(name, initializer)

    def _if(self):
        condition = self._expression()
        self._consume(T.LEFT_BRACE, "expected '{' after if condition")
        then_branch = nodes.Block(self._block())
        else_branch = None
        if self._match(T.ELSE):
            if self._match(T.IF):
                else_branch = self._if()
            else:
                self._consume(T.LEFT_BRACE, "expected '{' or 'if' after 'else'")
                else_branch = nodes.Block(self._block())
        return nodes.If(condition, then_branch, else_branch)

    def _while(self):
        condition = self._expression()
        self._consume(T.LEFT_BRACE, "expected '{' after while condition")
        body = self._loop_body()
        return nodes.While(condition, nodes.Block(body))

    def _for(self):
        var = self._consume(T.IDENTIFIER, "expected loop variable name after 'for'")
        self._consume(T.IN, "expected 'in' after loop variable")
        iterable = self._expression()
        self._consume(T.LEFT_BRACE, "expected '{' after for header")
        body = self._loop_body()
        return nodes.ForIn(var, iterable, nodes.Block(body))

    def _loop_body(self):
        self.loop_depth += 1
        try:
            return self._block()
        finally:
            self.loop_depth -= 1

    def _return(self):
        keyword = self._previous()
        if self.fn_depth == 0:
            raise self._error(keyword, "'return' outside of a function")
        value = None if self._check(T.SEMICOLON) else self._expression()
        self._consume(T.SEMICOLON, "expected ';' after return value")
        return nodes.Return(keyword, value)

    def _loop_jump(self, node_class, word):
        keyword = self._previous()
        if self.loop_depth == 0:
            raise self._error(keyword, f"'{word}' outside of a loop")
        self._consume(T.SEMICOLON, f"expected ';' after '{word}'")
        return node_class(keyword)

    def _function_decl(self):
        name = self._consume(T.IDENTIFIER, "expected function name")
        params, body = self._function_rest()
        return nodes.FunctionDecl(name, params, body)

    def _function_rest(self):
        """Parse `(params) { body }` and return (params, body statements)."""
        self._consume(T.LEFT_PAREN, "expected '(' before parameters")
        params = []
        if not self._check(T.RIGHT_PAREN):
            while True:
                param = self._consume(T.IDENTIFIER, "expected parameter name")
                if any(p.lexeme == param.lexeme for p in params):
                    raise self._error(param, f"duplicate parameter '{param.lexeme}'")
                params.append(param)
                if not self._match(T.COMMA):
                    break
        self._consume(T.RIGHT_PAREN, "expected ')' after parameters")
        self._consume(T.LEFT_BRACE, "expected '{' before function body")

        # break/continue must not reach across a function boundary
        saved_loop_depth, self.loop_depth = self.loop_depth, 0
        self.fn_depth += 1
        try:
            body = self._block()
        finally:
            self.fn_depth -= 1
            self.loop_depth = saved_loop_depth
        return params, body

    def _block(self):
        """Parse statements up to the closing brace. The '{' is already consumed."""
        statements = []
        while not self._check(T.RIGHT_BRACE) and not self._at_end():
            statements.append(self._statement())
        self._consume(T.RIGHT_BRACE, "expected '}' after block")
        return statements

    def _expression_statement(self):
        expr = self._expression()
        self._consume(T.SEMICOLON, "expected ';' after expression")
        return nodes.ExprStmt(expr)

    # -- expressions ------------------------------------------------------

    def _expression(self):
        return self._assignment()

    def _assignment(self):
        expr = self._or()
        if self._match(T.EQUAL):
            equals = self._previous()
            value = self._assignment()
            if isinstance(expr, (nodes.Variable, nodes.Index)):
                return nodes.Assign(expr, value, equals)
            raise self._error(equals, "invalid assignment target")
        return expr

    def _or(self):
        expr = self._and()
        while self._match(T.OR):
            expr = nodes.Logical(expr, self._previous(), self._and())
        return expr

    def _and(self):
        expr = self._not()
        while self._match(T.AND):
            expr = nodes.Logical(expr, self._previous(), self._not())
        return expr

    def _not(self):
        if self._match(T.NOT):
            return nodes.Unary(self._previous(), self._not())
        return self._equality()

    def _equality(self):
        return self._binary_left(self._comparison, T.EQUAL_EQUAL, T.NOT_EQUAL)

    def _comparison(self):
        return self._binary_left(self._term, T.LESS, T.LESS_EQUAL, T.GREATER, T.GREATER_EQUAL)

    def _term(self):
        return self._binary_left(self._factor, T.PLUS, T.MINUS)

    def _factor(self):
        return self._binary_left(self._unary, T.STAR, T.SLASH, T.PERCENT)

    def _binary_left(self, operand, *operators):
        expr = operand()
        while self._match(*operators):
            op = self._previous()
            expr = nodes.Binary(expr, op, operand())
        return expr

    def _unary(self):
        if self._match(T.MINUS):
            return nodes.Unary(self._previous(), self._unary())
        return self._postfix()

    def _postfix(self):
        expr = self._primary()
        while True:
            if self._match(T.LEFT_PAREN):
                expr = self._finish_call(expr)
            elif self._match(T.LEFT_BRACKET):
                bracket = self._previous()
                index = self._expression()
                self._consume(T.RIGHT_BRACKET, "expected ']' after index")
                expr = nodes.Index(expr, bracket, index)
            else:
                return expr

    def _finish_call(self, callee):
        args = []
        if not self._check(T.RIGHT_PAREN):
            while True:
                args.append(self._expression())
                if not self._match(T.COMMA):
                    break
        paren = self._consume(T.RIGHT_PAREN, "expected ')' after arguments")
        return nodes.Call(callee, paren, args)

    def _primary(self):
        if self._match(T.NUMBER, T.STRING):
            return nodes.Literal(self._previous().literal)
        if self._match(T.TRUE):
            return nodes.Literal(True)
        if self._match(T.FALSE):
            return nodes.Literal(False)
        if self._match(T.NIL):
            return nodes.Literal(None)
        if self._match(T.IDENTIFIER):
            return nodes.Variable(self._previous())
        if self._match(T.LEFT_PAREN):
            expr = self._expression()
            self._consume(T.RIGHT_PAREN, "expected ')' after expression")
            return expr
        if self._match(T.LEFT_BRACKET):
            return self._list_literal()
        if self._match(T.FN):
            keyword = self._previous()
            params, body = self._function_rest()
            return nodes.Lambda(keyword, params, body)
        raise self._error(self._peek(), "expected expression")

    def _list_literal(self):
        elements = []
        if not self._check(T.RIGHT_BRACKET):
            while True:
                elements.append(self._expression())
                if not self._match(T.COMMA):
                    break
        self._consume(T.RIGHT_BRACKET, "expected ']' after list elements")
        return nodes.ListLiteral(elements)

    # -- token helpers ----------------------------------------------------

    def _peek(self):
        return self.tokens[self.pos]

    def _peek_next(self):
        return self.tokens[min(self.pos + 1, len(self.tokens) - 1)]

    def _previous(self):
        return self.tokens[self.pos - 1]

    def _at_end(self):
        return self._peek().type == T.EOF

    def _check(self, type_):
        return self._peek().type == type_

    def _advance(self):
        token = self._peek()
        if not self._at_end():
            self.pos += 1
        return token

    def _match(self, *types):
        if self._peek().type in types:
            self._advance()
            return True
        return False

    def _consume(self, type_, message):
        if self._check(type_):
            return self._advance()
        raise self._error(self._peek(), message)

    def _error(self, token: Token, message):
        found = "end of file" if token.type == T.EOF else repr(token.lexeme)
        return ParseError(f"{message}, found {found}", token.line, token.column)
