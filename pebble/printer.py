"""Renders an AST as an S-expression string. Used by tests and `pebble --ast`."""

from . import nodes


def dump(node):
    match node:
        # expressions
        case nodes.Literal(value=v):
            return _literal(v)
        case nodes.Variable(name=name):
            return name.lexeme
        case nodes.Assign(target=target, value=value):
            return f"(= {dump(target)} {dump(value)})"
        case nodes.Unary(op=op, right=right):
            return f"({op.lexeme} {dump(right)})"
        case nodes.Binary(left=left, op=op, right=right) | nodes.Logical(left=left, op=op, right=right):
            return f"({op.lexeme} {dump(left)} {dump(right)})"
        case nodes.Call(callee=callee, args=args):
            return _form("call", dump(callee), *map(dump, args))
        case nodes.Index(obj=obj, index=index):
            return f"(index {dump(obj)} {dump(index)})"
        case nodes.ListLiteral(elements=elements):
            return _form("list", *map(dump, elements))
        case nodes.Lambda(params=params, body=body):
            return _form("fn", _params(params), *map(dump, body))

        # statements
        case nodes.ExprStmt(expression=e):
            return f"(expr {dump(e)})"
        case nodes.Let(name=name, initializer=init):
            return _form("let", name.lexeme, *([dump(init)] if init is not None else []))
        case nodes.Print(expression=e):
            return f"(print {dump(e)})"
        case nodes.Block(statements=statements):
            return _form("block", *map(dump, statements))
        case nodes.If(condition=c, then_branch=t, else_branch=e):
            return _form("if", dump(c), dump(t), *([dump(e)] if e is not None else []))
        case nodes.While(condition=c, body=body):
            return f"(while {dump(c)} {dump(body)})"
        case nodes.ForIn(var=var, iterable=it, body=body):
            return f"(for {var.lexeme} {dump(it)} {dump(body)})"
        case nodes.Return(value=v):
            return _form("return", *([dump(v)] if v is not None else []))
        case nodes.Break():
            return "(break)"
        case nodes.Continue():
            return "(continue)"
        case nodes.FunctionDecl(name=name, params=params, body=body):
            return _form("fn", name.lexeme, _params(params), *map(dump, body))
    raise TypeError(f"cannot dump {node!r}")


def _form(head, *parts):
    return "(" + " ".join([head, *parts]) + ")"


def _params(params):
    return "(" + " ".join(p.lexeme for p in params) + ")"


def _literal(value):
    if value is None:
        return "nil"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    return repr(value)
