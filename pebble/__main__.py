"""Command-line entry point: run a file, or start a REPL if no file is given."""

import argparse
import sys

from . import __version__, nodes
from .errors import PebbleError, PebbleRuntimeError
from .interpreter import Interpreter
from .lexer import Lexer
from .parser import Parser
from .printer import dump
from .values import stringify

EXIT_SYNTAX_ERROR = 65
EXIT_RUNTIME_ERROR = 70


def parse_source(source):
    return Parser(Lexer(source).tokenize()).parse()


def run_file(path, show_tokens=False, show_ast=False):
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as err:
        print(f"pebble: cannot read {path}: {err.strerror}", file=sys.stderr)
        return 1

    try:
        tokens = Lexer(source).tokenize()
        if show_tokens:
            for token in tokens:
                print(f"{token.line}:{token.column}\t{token.type.name}\t{token.lexeme!r}")
            return 0
        statements = Parser(tokens).parse()
        if show_ast:
            for stmt in statements:
                print(dump(stmt))
            return 0
        Interpreter().run(statements)
    except PebbleRuntimeError as err:
        print(err, file=sys.stderr)
        return EXIT_RUNTIME_ERROR
    except PebbleError as err:
        print(err, file=sys.stderr)
        return EXIT_SYNTAX_ERROR
    except RecursionError:
        print("Runtime error: expression nested too deeply", file=sys.stderr)
        return EXIT_RUNTIME_ERROR
    return 0


def _needs_more_input(text):
    """Rough check for an unfinished block: more '{' than '}' outside strings."""
    depth = 0
    in_string = False
    escaped = False
    for c in text:
        if in_string:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c in '"\n':
                in_string = False
        elif c == '"':
            in_string = True
        elif c == "#":
            break
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
    return depth > 0


def repl():
    print(f"Pebble {__version__}. Press Ctrl-D to exit.")
    interpreter = Interpreter()
    while True:
        try:
            source = input(">>> ")
            while _needs_more_input(source):
                source += "\n" + input("... ")
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print()
            continue

        stripped = source.strip()
        if not stripped:
            continue
        # Let a bare `1 + 2` or `print x` work without the trailing semicolon.
        if not stripped.endswith((";", "}")):
            source += ";"

        try:
            statements = parse_source(source)
            if len(statements) == 1 and isinstance(statements[0], nodes.ExprStmt):
                value = interpreter.evaluate(statements[0].expression)
                if value is not None:
                    print(stringify(value, nested=True))
            else:
                interpreter.run(statements)
        except PebbleError as err:
            print(err)
        except RecursionError:
            print("Runtime error: expression nested too deeply")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="pebble", description="The Pebble language interpreter.")
    parser.add_argument("script", nargs="?", help="a .pb file to run (omit to start the REPL)")
    parser.add_argument("--tokens", action="store_true", help="print the token stream and exit")
    parser.add_argument("--ast", action="store_true", help="print the syntax tree and exit")
    parser.add_argument("--version", action="version", version=f"pebble {__version__}")
    args = parser.parse_args(argv)

    if args.script is None:
        if args.tokens or args.ast:
            parser.error("--tokens and --ast need a script file")
        return repl()
    return run_file(args.script, show_tokens=args.tokens, show_ast=args.ast)


if __name__ == "__main__":
    sys.exit(main())
