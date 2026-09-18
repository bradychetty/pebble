# Pebble

Pebble is a small dynamically typed programming language, and this repo is a tree-walking interpreter for it, written in Python 3.10+ with no dependencies.

I built it to understand how a language works from source text through to execution: the lexer, the parser, scoping, closures, and error reporting. It is small enough to read in one sitting.

```
fn make_counter() {
    let count = 0;
    return fn() {
        count = count + 1;
        return count;
    };
}

let next = make_counter();
next();
print next();   # 2
```

## Quick start

```
git clone <this repo>
cd pebble

python3 -m pebble examples/fib.pb     # run a file
python3 -m pebble                     # start the REPL

python3 -m unittest discover -s tests # run the tests
```

`pip install -e .` also works and gives you a `pebble` command.

Two flags help when you want to see what the front end is doing:

```
$ python3 -m pebble --ast examples/hello.pb
(let name "Pebble")
(print (+ (+ "Hello from " name) "!"))
(print (* 6 7))

$ python3 -m pebble --tokens examples/hello.pb
2:1     LET     'let'
2:5     IDENTIFIER      'name'
2:10    EQUAL   '='
...
```

Syntax errors exit with code 65 and runtime errors with 70. Every error carries a line and column:

```
[line 2, col 9] Runtime error: '+' needs two numbers or two strings, got number and string
```

## The language

| Feature | Notes |
| --- | --- |
| Values | numbers (int and float), strings, `true`/`false`, `nil`, lists, functions |
| Variables | `let x = 1;` declares, `x = 2;` assigns. Blocks create a new scope. |
| Operators | `+ - * / %`, `== != < <= > >=`, `and`, `or`, `not`, unary `-` |
| Control flow | `if` / `else if` / `else`, `while`, `for x in list_or_string`, `break`, `continue` |
| Functions | `fn name(a, b) { ... }`, anonymous `fn(x) { ... }`, closures, recursion |
| Lists | `[1, 2, 3]`, `xs[0]`, `xs[-1]`, `xs[i] = v`. Lists are shared by reference. |
| Built-ins | `len`, `push`, `pop`, `str`, `num`, `type`, `range` |
| Output | `print expr;` |
| Comments | `# to end of line` |

Choices worth knowing about:

- **Truthiness:** only `nil` and `false` are falsy. `0` and `""` are truthy.
- **Equality:** `1 == true` is `false`. Values of different types are never equal, except that ints and floats compare by value.
- **Division:** `8 / 2` is `4` and `7 / 2` is `3.5`. Whole results stay integers, so big integers stay exact.
- **`and` / `or`** short-circuit and return the deciding operand, so `nil or "default"` is `"default"`.
- **Strict operators:** `1 + "a"` and `1 < "a"` are errors rather than silent conversions. Use `str()` and `num()`.
- **Loop variables:** each iteration of a `for` loop gets its own variable, so closures created in the loop capture that iteration's value.
- **Strings are immutable;** lists are not.
- **Recursion depth** is capped at 400 nested calls and reports a runtime error instead of crashing.

More programs are in [`examples/`](examples): closures, a prime sieve, quicksort, FizzBuzz.

## How it works

```
source text --> Lexer --> tokens --> Parser --> AST --> Interpreter --> output
               lexer.py            parser.py  nodes.py  interpreter.py
```

| File | Job |
| --- | --- |
| `pebble/tokens.py` | Token types and the keyword table |
| `pebble/lexer.py` | Source text to tokens, tracking line and column |
| `pebble/nodes.py` | AST node dataclasses |
| `pebble/parser.py` | Recursive-descent parser, one method per precedence level |
| `pebble/printer.py` | AST to S-expression text, for tests and `--ast` |
| `pebble/interpreter.py` | Walks the AST and executes it |
| `pebble/environment.py` | Scopes: a dict of names plus a link to the enclosing scope |
| `pebble/values.py` | Truthiness, equality, and how values print |
| `pebble/stdlib.py` | Built-in functions |
| `pebble/errors.py` | Error types with source positions |
| `pebble/__main__.py` | Command line and REPL |

Design notes:

- **Tree-walking.** The interpreter runs the AST directly using `match` on node types. This is slower than compiling to bytecode, but the code maps closely onto the language. `fib(24)` takes about a second.
- **Closures** work because a function keeps a reference to the scope it was defined in, and each call makes a new scope whose parent is that one.
- **`return`, `break` and `continue`** are implemented as exceptions that unwind the Python stack to the enclosing call or loop. The parser rejects them outside a function or loop, so the interpreter never sees a stray one.
- **The parser catches what it can early:** duplicate parameters, invalid assignment targets such as `f() = 3`, and `return` or `break` in the wrong place.
- **Blocks need braces,** and `{` never starts an expression, so `if x < 3 { ... }` parses without parentheses around the condition.

## Grammar

```
program     -> statement* EOF
statement   -> "let" IDENT ( "=" expr )? ";"
             | "fn" IDENT "(" params? ")" block
             | "print" expr ";"
             | "if" expr block ( "else" ( "if" ... | block ) )?
             | "while" expr block
             | "for" IDENT "in" expr block
             | "return" expr? ";"  |  "break" ";"  |  "continue" ";"
             | block
             | expr ";"
block       -> "{" statement* "}"

expr        -> assignment
assignment  -> ( variable | index ) "=" assignment | or
or          -> and ( "or" and )*
and         -> not ( "and" not )*
not         -> "not" not | equality
equality    -> comparison ( ( "==" | "!=" ) comparison )*
comparison  -> term ( ( "<" | "<=" | ">" | ">=" ) term )*
term        -> factor ( ( "+" | "-" ) factor )*
factor      -> unary ( ( "*" | "/" | "%" ) unary )*
unary       -> "-" unary | postfix
postfix     -> primary ( "(" args? ")" | "[" expr "]" )*
primary     -> NUMBER | STRING | "true" | "false" | "nil" | IDENT
             | "(" expr ")" | "[" args? "]" | "fn" "(" params? ")" block
```

## Tests

129 tests run with the standard library only: `python3 -m unittest discover -s tests`.

- `test_lexer.py`: tokens, escapes, positions, and lexical errors
- `test_parser.py`: precedence, associativity, statements, and parse errors. Trees are compared as S-expressions.
- `test_interpreter.py`: arithmetic, scoping, closures, control flow, lists, built-ins, and error positions
- `test_examples.py`: runs every program in `examples/` and compares against its `.expected` file
- `test_cli.py`: exit codes, `--ast`, `--tokens`, and the REPL

## Limitations and next steps

- Only the first syntax error is reported. Recovering after an error to report several would be a natural addition.
- No maps or objects, no modules, and no file or input functions.
- Variable lookup walks the scope chain by name at runtime. A resolver pass that computes each variable's depth ahead of time would be faster and would catch some mistakes before the program runs.
- Compiling to bytecode for a small VM would be the next step for speed.
