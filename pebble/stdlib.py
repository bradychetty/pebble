"""Built-in functions available in every Pebble program."""

import re

from .errors import PebbleRuntimeError
from .values import Builtin, is_number, stringify, type_name

_NUMBER_TEXT = re.compile(r"-?\d+(\.\d+)?")


def _fail(message):
    # The call site fills in the line number.
    return PebbleRuntimeError(message)


def _len(args):
    (value,) = args
    if isinstance(value, (list, str)):
        return len(value)
    raise _fail(f"len() expects a list or string, got {type_name(value)}")


def _push(args):
    target, value = args
    if not isinstance(target, list):
        raise _fail(f"push() expects a list as its first argument, got {type_name(target)}")
    target.append(value)
    return None


def _pop(args):
    (target,) = args
    if not isinstance(target, list):
        raise _fail(f"pop() expects a list, got {type_name(target)}")
    if not target:
        raise _fail("pop() from an empty list")
    return target.pop()


def _str(args):
    (value,) = args
    return stringify(value)


def _num(args):
    (value,) = args
    if is_number(value):
        return value
    if isinstance(value, str):
        text = value.strip()
        if _NUMBER_TEXT.fullmatch(text):
            return float(text) if "." in text else int(text)
        raise _fail(f'cannot convert "{value}" to a number')
    raise _fail(f"num() expects a string or number, got {type_name(value)}")


def _type(args):
    (value,) = args
    return type_name(value)


def _range(args):
    for a in args:
        if not isinstance(a, int) or isinstance(a, bool):
            raise _fail(f"range() expects integers, got {type_name(a)}")
    if len(args) == 1:
        start, stop, step = 0, args[0], 1
    elif len(args) == 2:
        start, stop, step = args[0], args[1], 1
    else:
        start, stop, step = args
    if step == 0:
        raise _fail("range() step cannot be zero")
    return list(range(start, stop, step))


def make_builtins():
    builtins = [
        Builtin("len", 1, 1, _len),
        Builtin("push", 2, 2, _push),
        Builtin("pop", 1, 1, _pop),
        Builtin("str", 1, 1, _str),
        Builtin("num", 1, 1, _num),
        Builtin("type", 1, 1, _type),
        Builtin("range", 1, 3, _range),
    ]
    return {b.name: b for b in builtins}
