"""AST node definitions.

Nodes keep the token they came from where a runtime error might need to point
at the source. Statements and expressions are plain dataclasses so the
interpreter can dispatch on them with `match`.
"""

from dataclasses import dataclass
from typing import Any, Optional

from .tokens import Token


# -- expressions ----------------------------------------------------------

@dataclass
class Literal:
    value: Any


@dataclass
class Variable:
    name: Token


@dataclass
class Assign:
    target: Any  # Variable or Index
    value: Any
    equals: Token


@dataclass
class Unary:
    op: Token
    right: Any


@dataclass
class Binary:
    left: Any
    op: Token
    right: Any


@dataclass
class Logical:
    left: Any
    op: Token
    right: Any


@dataclass
class Call:
    callee: Any
    paren: Token
    args: list


@dataclass
class Index:
    obj: Any
    bracket: Token
    index: Any


@dataclass
class ListLiteral:
    elements: list


@dataclass
class Lambda:
    keyword: Token
    params: list  # list[Token]
    body: list  # list of statements


# -- statements -----------------------------------------------------------

@dataclass
class ExprStmt:
    expression: Any


@dataclass
class Let:
    name: Token
    initializer: Optional[Any]


@dataclass
class Print:
    expression: Any


@dataclass
class Block:
    statements: list


@dataclass
class If:
    condition: Any
    then_branch: Block
    else_branch: Optional[Any]  # Block, If, or None


@dataclass
class While:
    condition: Any
    body: Block


@dataclass
class ForIn:
    var: Token
    iterable: Any
    body: Block


@dataclass
class Return:
    keyword: Token
    value: Optional[Any]


@dataclass
class Break:
    keyword: Token


@dataclass
class Continue:
    keyword: Token


@dataclass
class FunctionDecl:
    name: Token
    params: list  # list[Token]
    body: list  # list of statements
