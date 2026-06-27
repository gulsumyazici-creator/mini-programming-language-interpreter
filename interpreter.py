# Name Surname
# Gülsüm Yazıcı
# CmpE 260 Project 1 - Mini Programming Language Interpreter

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Any, List, Optional


# ----------------------------- Errors -----------------------------

class InterpreterError(Exception):
    pass


# ----------------------------- Lexer -----------------------------

@dataclass
class Token:
    type: str
    value: Any
    pos: int


KEYWORDS = {
    "let": "LET",
    "fun": "FUN",
    "if": "IF",
    "then": "THEN",
    "else": "ELSE",
    "end": "END",
    "and": "AND",
    "or": "OR",
    "not": "NOT",
    "true": "TRUE",
    "false": "FALSE",
    "print": "PRINT",
    # Bonus keywords are reserved even if the feature is not used.
    "while": "WHILE",
    "do": "DO",
    "length": "LENGTH",
    "append": "APPEND",
}


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.i = 0
        self.n = len(source)

    def current(self) -> str:
        if self.i >= self.n:
            return "\0"
        return self.source[self.i]

    def peek_char(self, offset: int = 1) -> str:
        j = self.i + offset
        if j >= self.n:
            return "\0"
        return self.source[j]

    def advance(self, count: int = 1) -> None:
        self.i += count

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []
        while self.i < self.n:
            c = self.current()

            if c.isspace():
                self.advance()
                continue

            # Block comments: (* ... *), not nested.
            if c == "(" and self.peek_char() == "*":
                self.skip_comment()
                continue

            start = self.i

            if c.isdigit():
                tokens.append(self.number())
                continue

            if c.isalpha():
                tokens.append(self.identifier_or_keyword())
                continue

            if c == '"':
                tokens.append(self.string())
                continue

            two = self.source[self.i:self.i + 2]
            if two == "->":
                tokens.append(Token("ARROW", "->", start))
                self.advance(2)
                continue
            if two == "==":
                tokens.append(Token("EQEQ", "==", start))
                self.advance(2)
                continue
            if two == "!=":
                tokens.append(Token("NEQ", "!=", start))
                self.advance(2)
                continue
            if two == "<=":
                tokens.append(Token("LE", "<=", start))
                self.advance(2)
                continue
            if two == ">=":
                tokens.append(Token("GE", ">=", start))
                self.advance(2)
                continue

            single = {
                "+": "PLUS",
                "-": "MINUS",
                "*": "STAR",
                "/": "SLASH",
                "<": "LT",
                ">": "GT",
                "=": "ASSIGN",
                "(": "LPAREN",
                ")": "RPAREN",
                "[": "LBRACKET",
                "]": "RBRACKET",
                ",": "COMMA",
                ";": "SEMI",
            }
            if c in single:
                tokens.append(Token(single[c], c, start))
                self.advance()
                continue

            raise InterpreterError(f"Lexical error at position {start}: unexpected character {c!r}")

        tokens.append(Token("EOF", None, self.i))
        return tokens

    def skip_comment(self) -> None:
        start = self.i
        self.advance(2)  # skip (*
        while self.i < self.n - 1:
            if self.current() == "*" and self.peek_char() == ")":
                self.advance(2)
                return
            self.advance()
        raise InterpreterError(f"Lexical error at position {start}: unterminated comment")

    def number(self) -> Token:
        start = self.i
        while self.current().isdigit():
            self.advance()
        return Token("NUMBER", int(self.source[start:self.i]), start)

    def identifier_or_keyword(self) -> Token:
        start = self.i
        while self.current().isalnum() or self.current() == "_":
            self.advance()
        text = self.source[start:self.i]
        typ = KEYWORDS.get(text, "IDENT")
        if typ == "TRUE":
            return Token("BOOL", True, start)
        if typ == "FALSE":
            return Token("BOOL", False, start)
        return Token(typ, text, start)

    def string(self) -> Token:
        start = self.i
        self.advance()  # opening quote
        chars: List[str] = []
        while self.i < self.n:
            c = self.current()
            if c == '"':
                self.advance()
                return Token("STRING", "".join(chars), start)
            if c == "\\":
                self.advance()
                esc = self.current()
                mapping = {"n": "\n", "t": "\t", "\\": "\\", '"': '"'}
                if esc not in mapping:
                    raise InterpreterError(f"Lexical error at position {self.i}: invalid escape sequence \\{esc}")
                chars.append(mapping[esc])
                self.advance()
            else:
                chars.append(c)
                self.advance()
        raise InterpreterError(f"Lexical error at position {start}: unterminated string literal")


# ----------------------------- AST nodes -----------------------------

@dataclass
class Block:
    statements: List[Any]
    final_expr: Optional[Any]


@dataclass
class NumberLit:
    value: int


@dataclass
class BoolLit:
    value: bool


@dataclass
class StringLit:
    value: str


@dataclass
class ListLit:
    elements: List[Any]


@dataclass
class Identifier:
    name: str


@dataclass
class BinOp:
    op: str
    left: Any
    right: Any


@dataclass
class UnaryOp:
    op: str
    expr: Any


@dataclass
class IfExpr:
    cond: Any
    then_branch: Block
    else_branch: Block


@dataclass
class FunExpr:
    params: List[str]
    body: Block


@dataclass
class CallExpr:
    func: Any
    args: List[Any]


@dataclass
class BuiltinCall:
    name: str
    args: List[Any]


@dataclass
class IndexExpr:
    collection: Any
    index: Any


@dataclass
class LetStmt:
    name: str
    value: Any


@dataclass
class AssignStmt:
    name: str
    value: Any


@dataclass
class PrintStmt:
    expr: Any


@dataclass
class ExprStmt:
    expr: Any


@dataclass
class WhileStmt:
    cond: Any
    body: Block


# ----------------------------- Parser -----------------------------

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.i = 0

    def current(self) -> Token:
        return self.tokens[self.i]

    def peek(self, offset: int = 1) -> Token:
        j = self.i + offset
        if j >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[j]

    def match(self, *types: str) -> Optional[Token]:
        if self.current().type in types:
            tok = self.current()
            self.i += 1
            return tok
        return None

    def consume(self, typ: str, message: str) -> Token:
        tok = self.match(typ)
        if tok is None:
            cur = self.current()
            raise InterpreterError(f"Syntax error at position {cur.pos}: {message}; found {cur.type}")
        return tok

    def parse(self) -> Block:
        block = self.parse_block({"EOF"})
        self.consume("EOF", "expected end of file")
        return block

    def parse_block(self, stop_types: set[str]) -> Block:
        statements: List[Any] = []
        final_expr: Optional[Any] = None

        while self.current().type not in stop_types:
            if self.current().type == "EOF":
                raise InterpreterError("Syntax error: unexpected end of file in block")

            if self.is_statement_start():
                stmt = self.parse_statement()
                if self.match("SEMI"):
                    statements.append(stmt)
                    continue
                if self.current().type in stop_types:
                    # A small extension: allow the last statement before 'end' to omit ';'.
                    statements.append(stmt)
                    break
                cur = self.current()
                raise InterpreterError(f"Syntax error at position {cur.pos}: expected ';'")

            expr = self.parse_expr()
            if self.match("SEMI"):
                statements.append(ExprStmt(expr))
                continue

            final_expr = expr
            if self.current().type not in stop_types:
                cur = self.current()
                raise InterpreterError(f"Syntax error at position {cur.pos}: expected ';' or block terminator")
            break

        return Block(statements, final_expr)

    def is_statement_start(self) -> bool:
        typ = self.current().type
        if typ in {"LET", "PRINT", "WHILE"}:
            return True
        if typ == "IDENT" and self.peek().type == "ASSIGN":
            return True
        return False

    def parse_statement(self) -> Any:
        typ = self.current().type
        if typ == "LET":
            return self.parse_let()
        if typ == "PRINT":
            return self.parse_print()
        if typ == "WHILE":
            return self.parse_while()
        if typ == "IDENT" and self.peek().type == "ASSIGN":
            return self.parse_assign()
        raise InterpreterError(f"Syntax error at position {self.current().pos}: expected statement")

    def parse_let(self) -> LetStmt:
        self.consume("LET", "expected 'let'")
        name = self.consume("IDENT", "expected identifier after 'let'").value
        self.consume("ASSIGN", "expected '=' in let statement")
        value = self.parse_expr()
        return LetStmt(name, value)

    def parse_assign(self) -> AssignStmt:
        name = self.consume("IDENT", "expected identifier").value
        self.consume("ASSIGN", "expected '=' in assignment")
        value = self.parse_expr()
        return AssignStmt(name, value)

    def parse_print(self) -> PrintStmt:
        self.consume("PRINT", "expected 'print'")
        self.consume("LPAREN", "expected '(' after print")
        expr = self.parse_expr()
        self.consume("RPAREN", "expected ')' after print argument")
        return PrintStmt(expr)

    def parse_while(self) -> WhileStmt:
        self.consume("WHILE", "expected 'while'")
        cond = self.parse_expr()
        self.consume("DO", "expected 'do' after while condition")
        body = self.parse_block({"END"})
        self.consume("END", "expected 'end' after while body")
        return WhileStmt(cond, body)

    # Precedence level 1: or
    def parse_expr(self) -> Any:
        return self.parse_or()

    def parse_or(self) -> Any:
        expr = self.parse_and()
        while self.match("OR"):
            expr = BinOp("or", expr, self.parse_and())
        return expr

    # Precedence level 2: and
    def parse_and(self) -> Any:
        expr = self.parse_compare()
        while self.match("AND"):
            expr = BinOp("and", expr, self.parse_compare())
        return expr

    # Precedence level 3: comparisons, non-associative
    def parse_compare(self) -> Any:
        expr = self.parse_add()
        comp_map = {
            "EQEQ": "==",
            "NEQ": "!=",
            "LT": "<",
            "GT": ">",
            "LE": "<=",
            "GE": ">=",
        }
        if self.current().type in comp_map:
            op = comp_map[self.current().type]
            self.i += 1
            expr = BinOp(op, expr, self.parse_add())
            if self.current().type in comp_map:
                raise InterpreterError(f"Syntax error at position {self.current().pos}: chained comparisons are not allowed")
        return expr

    # Precedence level 4: +, -
    def parse_add(self) -> Any:
        expr = self.parse_mul()
        while self.current().type in {"PLUS", "MINUS"}:
            if self.match("PLUS"):
                op = "+"
            else:
                self.consume("MINUS", "expected '-' or '+'")
                op = "-"
            expr = BinOp(op, expr, self.parse_mul())
        return expr

    # Precedence level 5: *, /
    def parse_mul(self) -> Any:
        expr = self.parse_unary()
        while self.current().type in {"STAR", "SLASH"}:
            if self.match("STAR"):
                op = "*"
            else:
                self.consume("SLASH", "expected '*' or '/'")
                op = "/"
            expr = BinOp(op, expr, self.parse_unary())
        return expr

    # Precedence level 6: not, unary -
    def parse_unary(self) -> Any:
        if self.match("NOT"):
            return UnaryOp("not", self.parse_unary())
        if self.match("MINUS"):
            return UnaryOp("-", self.parse_unary())
        return self.parse_call_index()

    # Precedence level 7: function call and indexing
    def parse_call_index(self) -> Any:
        expr = self.parse_primary()
        while True:
            if self.match("LPAREN"):
                args: List[Any] = []
                if not self.match("RPAREN"):
                    args.append(self.parse_expr())
                    while self.match("COMMA"):
                        args.append(self.parse_expr())
                    self.consume("RPAREN", "expected ')' after arguments")
                expr = CallExpr(expr, args)
                continue
            if self.match("LBRACKET"):
                idx = self.parse_expr()
                self.consume("RBRACKET", "expected ']' after index")
                expr = IndexExpr(expr, idx)
                continue
            break
        return expr

    def parse_primary(self) -> Any:
        tok = self.current()
        if self.match("NUMBER"):
            return NumberLit(tok.value)
        if self.match("BOOL"):
            return BoolLit(tok.value)
        if self.match("STRING"):
            return StringLit(tok.value)
        if self.match("IDENT"):
            return Identifier(tok.value)
        if self.match("LPAREN"):
            expr = self.parse_expr()
            self.consume("RPAREN", "expected ')' after expression")
            return expr
        if self.current().type == "IF":
            return self.parse_if()
        if self.current().type == "FUN":
            return self.parse_fun()
        if self.current().type == "LBRACKET":
            return self.parse_list_literal()
        if self.current().type in {"LENGTH", "APPEND"}:
            return self.parse_builtin_call()
        raise InterpreterError(f"Syntax error at position {tok.pos}: expected expression")

    def parse_if(self) -> IfExpr:
        self.consume("IF", "expected 'if'")
        cond = self.parse_expr()
        self.consume("THEN", "expected 'then' after condition")
        then_branch = self.parse_block({"ELSE"})
        self.consume("ELSE", "expected 'else' in if expression")
        else_branch = self.parse_block({"END"})
        self.consume("END", "expected 'end' after if expression")
        return IfExpr(cond, then_branch, else_branch)

    def parse_fun(self) -> FunExpr:
        self.consume("FUN", "expected 'fun'")
        self.consume("LPAREN", "expected '(' after fun")
        params: List[str] = []
        if not self.match("RPAREN"):
            params.append(self.consume("IDENT", "expected parameter name").value)
            while self.match("COMMA"):
                params.append(self.consume("IDENT", "expected parameter name after ','").value)
            self.consume("RPAREN", "expected ')' after parameters")
        self.consume("ARROW", "expected '->' after function parameters")
        body = self.parse_block({"END"})
        self.consume("END", "expected 'end' after function body")
        return FunExpr(params, body)

    def parse_list_literal(self) -> ListLit:
        self.consume("LBRACKET", "expected '['")
        elements: List[Any] = []
        if not self.match("RBRACKET"):
            elements.append(self.parse_expr())
            while self.match("COMMA"):
                elements.append(self.parse_expr())
            self.consume("RBRACKET", "expected ']' after list literal")
        return ListLit(elements)

    def parse_builtin_call(self) -> BuiltinCall:
        name = self.current().value
        self.i += 1
        self.consume("LPAREN", f"expected '(' after {name}")
        args: List[Any] = []
        if not self.match("RPAREN"):
            args.append(self.parse_expr())
            while self.match("COMMA"):
                args.append(self.parse_expr())
            self.consume("RPAREN", f"expected ')' after {name} arguments")
        return BuiltinCall(name, args)


# ----------------------------- Environment and values -----------------------------

class Env:
    def __init__(self, parent: Optional[Env] = None):
        self.parent = parent
        self.values: dict[str, Any] = {}

    def define(self, name: str, value: Any) -> None:
        # Re-declaration in the same frame is allowed and shadows/overwrites that frame's old binding.
        self.values[name] = value

    def lookup(self, name: str) -> Any:
        if name in self.values:
            return self.values[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        raise InterpreterError(f"Undefined variable: {name}")

    def assign(self, name: str, value: Any) -> None:
        if name in self.values:
            self.values[name] = value
            return
        if self.parent is not None:
            self.parent.assign(name, value)
            return
        raise InterpreterError(f"Undefined variable: {name}")


@dataclass
class Closure:
    params: List[str]
    body: Block
    env: Env


# ----------------------------- Evaluator -----------------------------

class Evaluator:
    def __init__(self, scope: str = "static"):
        if scope not in {"static", "dynamic"}:
            raise InterpreterError("Scope must be 'static' or 'dynamic'")
        self.scope = scope

    def eval_program(self, program: Block) -> Any:
        return self.eval_block(program, Env())

    def eval_block(self, block: Block, env: Env) -> Any:
        result = None
        for stmt in block.statements:
            result = self.eval_stmt(stmt, env)
        if block.final_expr is not None:
            result = self.eval_expr(block.final_expr, env)
        return result

    def eval_stmt(self, stmt: Any, env: Env) -> Any:
        if isinstance(stmt, LetStmt):
            # Implicit recursion for let-bound functions.
            if isinstance(stmt.value, FunExpr):
                env.define(stmt.name, None)
                value = self.eval_expr(stmt.value, env)
                env.assign(stmt.name, value)
            else:
                value = self.eval_expr(stmt.value, env)
                env.define(stmt.name, value)
            return None

        if isinstance(stmt, AssignStmt):
            value = self.eval_expr(stmt.value, env)
            env.assign(stmt.name, value)
            return None

        if isinstance(stmt, PrintStmt):
            value = self.eval_expr(stmt.expr, env)
            print(format_value(value, in_list=False))
            return None

        if isinstance(stmt, ExprStmt):
            return self.eval_expr(stmt.expr, env)

        if isinstance(stmt, WhileStmt):
            while True:
                cond = self.eval_expr(stmt.cond, env)
                require_bool(cond, "while condition")
                if not cond:
                    break
                self.eval_block(stmt.body, env)
            return None

        raise InterpreterError(f"Internal error: unknown statement {type(stmt).__name__}")

    def eval_expr(self, expr: Any, env: Env) -> Any:
        if isinstance(expr, NumberLit):
            return expr.value
        if isinstance(expr, BoolLit):
            return expr.value
        if isinstance(expr, StringLit):
            return expr.value
        if isinstance(expr, ListLit):
            return [self.eval_expr(e, env) for e in expr.elements]
        if isinstance(expr, Identifier):
            return env.lookup(expr.name)
        if isinstance(expr, UnaryOp):
            return self.eval_unary(expr, env)
        if isinstance(expr, BinOp):
            return self.eval_binary(expr, env)
        if isinstance(expr, IfExpr):
            cond = self.eval_expr(expr.cond, env)
            require_bool(cond, "if condition")
            if cond:
                return self.eval_block(expr.then_branch, env)
            return self.eval_block(expr.else_branch, env)
        if isinstance(expr, FunExpr):
            return Closure(expr.params, expr.body, env)
        if isinstance(expr, CallExpr):
            return self.eval_call(expr, env)
        if isinstance(expr, BuiltinCall):
            return self.eval_builtin(expr, env)
        if isinstance(expr, IndexExpr):
            collection = self.eval_expr(expr.collection, env)
            index = self.eval_expr(expr.index, env)
            require_int(index, "list index")
            if not isinstance(collection, list):
                raise InterpreterError("Type error: indexing requires a list")
            if index < 0 or index >= len(collection):
                raise InterpreterError("Runtime error: list index out of range")
            return collection[index]
        raise InterpreterError(f"Internal error: unknown expression {type(expr).__name__}")

    def eval_unary(self, expr: UnaryOp, env: Env) -> Any:
        value = self.eval_expr(expr.expr, env)
        if expr.op == "not":
            require_bool(value, "operator not")
            return not value
        if expr.op == "-":
            require_int(value, "unary minus")
            return -value
        raise InterpreterError(f"Internal error: unknown unary operator {expr.op}")

    def eval_binary(self, expr: BinOp, env: Env) -> Any:
        op = expr.op

        # Short-circuit logical operators.
        if op == "and":
            left = self.eval_expr(expr.left, env)
            require_bool(left, "operator and")
            if not left:
                return False
            right = self.eval_expr(expr.right, env)
            require_bool(right, "operator and")
            return left and right

        if op == "or":
            left = self.eval_expr(expr.left, env)
            require_bool(left, "operator or")
            if left:
                return True
            right = self.eval_expr(expr.right, env)
            require_bool(right, "operator or")
            return left or right

        left = self.eval_expr(expr.left, env)
        right = self.eval_expr(expr.right, env)

        if op == "+":
            if is_int(left) and is_int(right):
                return left + right
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            raise InterpreterError("Type error: operator + requires two integers or two strings")

        if op == "-":
            require_int(left, "operator -")
            require_int(right, "operator -")
            return left - right

        if op == "*":
            require_int(left, "operator *")
            require_int(right, "operator *")
            return left * right

        if op == "/":
            require_int(left, "operator /")
            require_int(right, "operator /")
            if right == 0:
                raise InterpreterError("Runtime error: division by zero")
            return trunc_div(left, right)

        if op in {"<", ">", "<=", ">="}:
            require_int(left, f"operator {op}")
            require_int(right, f"operator {op}")
            if op == "<":
                return left < right
            if op == ">":
                return left > right
            if op == "<=":
                return left <= right
            return left >= right

        if op == "==":
            return values_equal(left, right)
        if op == "!=":
            return not values_equal(left, right)

        raise InterpreterError(f"Internal error: unknown binary operator {op}")

    def eval_call(self, expr: CallExpr, env: Env) -> Any:
        func = self.eval_expr(expr.func, env)
        if not isinstance(func, Closure):
            raise InterpreterError("Type error: attempted to call a non-function value")

        if len(expr.args) != len(func.params):
            raise InterpreterError(
                f"Arity error: expected {len(func.params)} arguments, got {len(expr.args)}"
            )

        # Call-by-value: evaluate argument expressions before creating parameter bindings.
        arg_values = [self.eval_expr(arg, env) for arg in expr.args]

        parent = func.env if self.scope == "static" else env
        call_env = Env(parent)
        for param, value in zip(func.params, arg_values):
            call_env.define(param, value)
        return self.eval_block(func.body, call_env)

    def eval_builtin(self, expr: BuiltinCall, env: Env) -> Any:
        if expr.name == "length":
            if len(expr.args) != 1:
                raise InterpreterError("Arity error: length expects 1 argument")
            value = self.eval_expr(expr.args[0], env)
            if isinstance(value, (str, list)):
                return len(value)
            raise InterpreterError("Type error: length expects a string or list")

        if expr.name == "append":
            if len(expr.args) != 2:
                raise InterpreterError("Arity error: append expects 2 arguments")
            lst = self.eval_expr(expr.args[0], env)
            if not isinstance(lst, list):
                raise InterpreterError("Type error: append expects a list as first argument")
            value = self.eval_expr(expr.args[1], env)
            lst.append(value)
            return lst

        raise InterpreterError(f"Unknown built-in function: {expr.name}")


# ----------------------------- Helpers -----------------------------

def is_int(value: Any) -> bool:
    return type(value) is int


def require_int(value: Any, context: str) -> None:
    if not is_int(value):
        raise InterpreterError(f"Type error: {context} requires integer operands")


def require_bool(value: Any, context: str) -> None:
    if type(value) is not bool:
        raise InterpreterError(f"Type error: {context} requires boolean operands")


def trunc_div(a: int, b: int) -> int:
    q = abs(a) // abs(b)
    if (a < 0) ^ (b < 0):
        return -q
    return q


def values_equal(a: Any, b: Any) -> bool:
    if isinstance(a, Closure) or isinstance(b, Closure):
        return a is b
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return False
        return all(values_equal(x, y) for x, y in zip(a, b))
    if type(a) is not type(b):
        return False
    return a == b


def format_value(value: Any, in_list: bool = False) -> str:
    if type(value) is bool:
        return "true" if value else "false"
    if type(value) is int:
        return str(value)
    if isinstance(value, str):
        return quote_string(value) if in_list else value
    if isinstance(value, list):
        return "[" + ", ".join(format_value(v, in_list=True) for v in value) + "]"
    if isinstance(value, Closure):
        return "<function>"
    if value is None:
        return "undefined"
    return str(value)


def quote_string(s: str) -> str:
    escaped = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")
    return '"' + escaped + '"'


def run_source(source: str, scope: str) -> Any:
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()
    return Evaluator(scope=scope).eval_program(program)


# ----------------------------- CLI -----------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="CmpE 260 Mini Language Interpreter")
    parser.add_argument("--scope", choices=["static", "dynamic"], default="static")
    parser.add_argument("program", help="path to the source program file")
    args = parser.parse_args(argv)

    try:
        with open(args.program, "r", encoding="utf-8") as f:
            source = f.read()
        run_source(source, scope=args.scope)
        return 0
    except InterpreterError as e:
        print(str(e), file=sys.stderr)
        return 1
    except OSError as e:
        print(f"File error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
