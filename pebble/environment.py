from .errors import PebbleRuntimeError


class Environment:
    """A scope: a dict of names plus a link to the enclosing scope."""

    def __init__(self, parent=None):
        self.values = {}
        self.parent = parent

    def define(self, name, value):
        self.values[name] = value

    def get(self, token):
        env = self
        while env is not None:
            if token.lexeme in env.values:
                return env.values[token.lexeme]
            env = env.parent
        raise self._undefined(token)

    def assign(self, token, value):
        env = self
        while env is not None:
            if token.lexeme in env.values:
                env.values[token.lexeme] = value
                return
            env = env.parent
        raise self._undefined(token)

    @staticmethod
    def _undefined(token):
        return PebbleRuntimeError(f"undefined variable '{token.lexeme}'", token.line, token.column)
