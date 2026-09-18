"""Runtime value helpers.

Pebble values map onto Python values:

    nil -> None          bool -> bool          number -> int or float
    string -> str        list -> list          function -> PebbleFunction / Builtin
"""

from dataclasses import dataclass
from typing import Callable


class PebbleFunction:
    def __init__(self, name, params, body, closure):
        self.name = name
        self.params = params  # list of parameter names (str)
        self.body = body  # list of statements
        self.closure = closure  # Environment the function was defined in

    @property
    def arity(self):
        return len(self.params)


@dataclass
class Builtin:
    name: str
    min_args: int
    max_args: int
    fn: Callable


def is_number(value):
    # bool is a subclass of int in Python, so it has to be excluded by hand
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_truthy(value):
    return value is not None and value is not False


def type_name(value):
    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "bool"
    if is_number(value):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "list"
    return "function"


def values_equal(a, b):
    if a is None or b is None:
        return a is b
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if is_number(a) and is_number(b):
        return a == b
    if isinstance(a, str) and isinstance(b, str):
        return a == b
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(values_equal(x, y) for x, y in zip(a, b))
    return a is b


def stringify(value, nested=False, _seen=None):
    """Text form of a value. Strings are quoted only when inside a list."""
    if value is None:
        return "nil"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else repr(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return f'"{value}"' if nested else value
    if isinstance(value, list):
        seen = _seen if _seen is not None else set()
        if id(value) in seen:
            return "[...]"
        seen.add(id(value))
        try:
            return "[" + ", ".join(stringify(v, True, seen) for v in value) + "]"
        finally:
            seen.discard(id(value))
    if isinstance(value, PebbleFunction):
        return f"<fn {value.name}>"
    if isinstance(value, Builtin):
        return f"<builtin {value.name}>"
    return repr(value)
