"""Turns source text into a list of tokens."""

from .errors import LexError
from .tokens import KEYWORDS, Token, TokenType

_SINGLE_CHAR = {
    "(": TokenType.LEFT_PAREN,
    ")": TokenType.RIGHT_PAREN,
    "{": TokenType.LEFT_BRACE,
    "}": TokenType.RIGHT_BRACE,
    "[": TokenType.LEFT_BRACKET,
    "]": TokenType.RIGHT_BRACKET,
    ",": TokenType.COMMA,
    ";": TokenType.SEMICOLON,
    "+": TokenType.PLUS,
    "-": TokenType.MINUS,
    "*": TokenType.STAR,
    "/": TokenType.SLASH,
    "%": TokenType.PERCENT,
}

_ESCAPES = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}


def _is_digit(c):
    return c.isascii() and c.isdigit()


def _is_alpha(c):
    return c.isascii() and (c.isalpha() or c == "_")


class Lexer:
    def __init__(self, source):
        self.source = source
        self.tokens = []
        self.start = 0
        self.current = 0
        self.line = 1
        self.line_start = 0

    def tokenize(self):
        while not self._at_end():
            self.start = self.current
            self._scan_token()
        self.tokens.append(Token(TokenType.EOF, "", None, self.line, self._column()))
        return self.tokens

    # -- scanning ---------------------------------------------------------

    def _scan_token(self):
        c = self._advance()

        if c in _SINGLE_CHAR:
            self._add(_SINGLE_CHAR[c])
        elif c == "=":
            self._add(TokenType.EQUAL_EQUAL if self._match("=") else TokenType.EQUAL)
        elif c == "<":
            self._add(TokenType.LESS_EQUAL if self._match("=") else TokenType.LESS)
        elif c == ">":
            self._add(TokenType.GREATER_EQUAL if self._match("=") else TokenType.GREATER)
        elif c == "!":
            if self._match("="):
                self._add(TokenType.NOT_EQUAL)
            else:
                raise self._error("unexpected '!' (use 'not' for negation)")
        elif c == "#":
            while not self._at_end() and self._peek() != "\n":
                self._advance()
        elif c in " \r\t":
            pass
        elif c == "\n":
            self.line += 1
            self.line_start = self.current
        elif c == '"':
            self._string()
        elif _is_digit(c):
            self._number()
        elif _is_alpha(c):
            self._identifier()
        else:
            raise self._error(f"unexpected character {c!r}")

    def _number(self):
        while _is_digit(self._peek()):
            self._advance()
        if self._peek() == "." and _is_digit(self._peek_next()):
            self._advance()
            while _is_digit(self._peek()):
                self._advance()
        text = self.source[self.start:self.current]
        value = float(text) if "." in text else int(text)
        self._add(TokenType.NUMBER, value)

    def _identifier(self):
        while _is_alpha(self._peek()) or _is_digit(self._peek()):
            self._advance()
        text = self.source[self.start:self.current]
        self._add(KEYWORDS.get(text, TokenType.IDENTIFIER))

    def _string(self):
        chars = []
        while True:
            if self._at_end() or self._peek() == "\n":
                raise self._error("unterminated string")
            c = self._advance()
            if c == '"':
                break
            if c == "\\":
                if self._at_end():
                    raise self._error("unterminated string")
                esc = self._advance()
                if esc not in _ESCAPES:
                    raise self._error(f"invalid escape sequence '\\{esc}'")
                chars.append(_ESCAPES[esc])
            else:
                chars.append(c)
        self._add(TokenType.STRING, "".join(chars))

    # -- helpers ----------------------------------------------------------

    def _at_end(self):
        return self.current >= len(self.source)

    def _advance(self):
        c = self.source[self.current]
        self.current += 1
        return c

    def _peek(self):
        return "\0" if self._at_end() else self.source[self.current]

    def _peek_next(self):
        if self.current + 1 >= len(self.source):
            return "\0"
        return self.source[self.current + 1]

    def _match(self, expected):
        if self._at_end() or self.source[self.current] != expected:
            return False
        self.current += 1
        return True

    def _column(self, index=None):
        index = self.current if index is None else index
        return index - self.line_start + 1

    def _add(self, type_, literal=None):
        lexeme = self.source[self.start:self.current]
        self.tokens.append(Token(type_, lexeme, literal, self.line, self._column(self.start)))

    def _error(self, message):
        return LexError(message, self.line, self._column(self.start))
