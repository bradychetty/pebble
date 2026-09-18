"""Error types. Every error carries a source position so messages can point at it."""


class PebbleError(Exception):
    kind = "Error"

    def __init__(self, message, line=None, column=None):
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column

    def __str__(self):
        if self.line is None:
            return f"{self.kind}: {self.message}"
        where = f"line {self.line}"
        if self.column is not None:
            where += f", col {self.column}"
        return f"[{where}] {self.kind}: {self.message}"


class LexError(PebbleError):
    kind = "Syntax error"


class ParseError(PebbleError):
    kind = "Syntax error"


class PebbleRuntimeError(PebbleError):
    kind = "Runtime error"
