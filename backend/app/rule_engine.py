from dataclasses import dataclass
from typing import Any, Callable

from . import models
from .rule_context import build_functions, build_series_context
from .series import SeriesAccessor


@dataclass
class EvaluationResult:
    decision: str
    action: str
    state_key: str
    reasons: list[dict[str, str]]


class Token:
    def __init__(self, kind: str, value: str):
        self.kind = kind
        self.value = value

    def __repr__(self):
        return f"Token({self.kind}, {self.value})"


class Lexer:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0

    def _peek(self) -> str:
        if self.pos >= len(self.text):
            return ""
        return self.text[self.pos]

    def _advance(self):
        self.pos += 1

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        while self.pos < len(self.text):
            ch = self._peek()
            if ch.isspace():
                self._advance()
                continue
            if ch.isdigit() or ch == ".":
                tokens.append(self._number())
                continue
            if ch.isalpha() or ch in "_.":
                tokens.append(self._identifier())
                continue
            if ch in "+-*/()[],":
                tokens.append(Token(ch, ch))
                self._advance()
                continue
            if ch in "><=":
                tokens.append(self._operator())
                continue
            raise ValueError(f"Unexpected character: {ch}")
        return tokens

    def _number(self) -> Token:
        start = self.pos
        dot_seen = False
        while self.pos < len(self.text):
            ch = self._peek()
            if ch == ".":
                if dot_seen:
                    break
                dot_seen = True
                self._advance()
                continue
            if not ch.isdigit():
                break
            self._advance()
        return Token("NUMBER", self.text[start:self.pos])

    def _identifier(self) -> Token:
        start = self.pos
        while self.pos < len(self.text):
            ch = self._peek()
            if ch.isalnum() or ch in "_.":
                self._advance()
                continue
            break
        value = self.text[start:self.pos]
        upper = value.upper()
        if upper in {"AND", "OR", "NOT"}:
            return Token(upper, upper)
        if upper in {"GT", "GTE", "LT", "LTE", "EQ", "NE", "ABOVE", "BELOW", "CROSSOVER", "CROSSUNDER"}:
            return Token("OP", upper)
        return Token("IDENT", value)

    def _operator(self) -> Token:
        start = self.pos
        self._advance()
        if self.pos < len(self.text) and self.text[self.pos] == "=":
            self._advance()
        return Token("OP", self.text[start:self.pos])


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def _peek(self) -> Token | None:
        if self.pos >= len(self.tokens):
            return None
        return self.tokens[self.pos]

    def _advance(self) -> Token:
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def parse(self):
        expr = self._parse_or()
        if self._peek() is not None:
            raise ValueError("Unexpected token at end")
        return expr

    def _parse_or(self):
        node = self._parse_and()
        while self._peek() and self._peek().kind == "OR":
            self._advance()
            right = self._parse_and()
            node = ("or", node, right)
        return node

    def _parse_and(self):
        node = self._parse_not()
        while self._peek() and self._peek().kind == "AND":
            self._advance()
            right = self._parse_not()
            node = ("and", node, right)
        return node

    def _parse_not(self):
        if self._peek() and self._peek().kind == "NOT":
            self._advance()
            operand = self._parse_not()
            return ("not", operand)
        return self._parse_compare()

    def _parse_compare(self):
        node = self._parse_additive()
        while self._peek() and self._peek().kind == "OP":
            op = self._advance().value
            right = self._parse_additive()
            node = ("cmp", op, node, right)
        return node

    def _parse_additive(self):
        node = self._parse_multiplicative()
        while self._peek() and self._peek().kind in {"+", "-"}:
            op = self._advance().value
            right = self._parse_multiplicative()
            node = ("bin", op, node, right)
        return node

    def _parse_multiplicative(self):
        node = self._parse_unary()
        while self._peek() and self._peek().kind in {"*", "/"}:
            op = self._advance().value
            right = self._parse_unary()
            node = ("bin", op, node, right)
        return node

    def _parse_unary(self):
        if self._peek() and self._peek().kind in {"+", "-"}:
            op = self._advance().value
            operand = self._parse_unary()
            return ("unary", op, operand)
        return self._parse_postfix()

    def _parse_postfix(self):
        node = self._parse_primary()
        while self._peek() and self._peek().kind == "[":
            self._advance()
            index = self._parse_or()
            if not self._peek() or self._peek().kind != "]":
                raise ValueError("Missing closing bracket")
            self._advance()
            node = ("index", node, index)
        return node

    def _parse_primary(self):
        token = self._peek()
        if token is None:
            raise ValueError("Unexpected end of input")
        if token.kind == "NUMBER":
            self._advance()
            return ("number", float(token.value))
        if token.kind == "IDENT":
            self._advance()
            if self._peek() and self._peek().kind == "(":
                self._advance()
                args = []
                if self._peek() and self._peek().kind != ")":
                    args.append(self._parse_or())
                    while self._peek() and self._peek().kind == ",":
                        self._advance()
                        args.append(self._parse_or())
                if not self._peek() or self._peek().kind != ")":
                    raise ValueError("Missing closing parenthesis")
                self._advance()
                return ("call", token.value, args)
            return ("ident", token.value)
        if token.kind == "(":
            self._advance()
            expr = self._parse_or()
            if not self._peek() or self._peek().kind != ")":
                raise ValueError("Missing closing parenthesis")
            self._advance()
            return expr
        raise ValueError(f"Unexpected token: {token}")


class ExpressionEvaluator:
    def __init__(self, context: dict[str, Any], functions: dict[str, Callable]):
        self.context = context
        self.functions = functions

    def eval(self, node, offset: int = 0, preserve_series: bool = False):
        kind = node[0]
        if kind == "number":
            return node[1]
        if kind == "ident":
            value = self.context.get(node[1])
            return self._resolve_value(value, offset, preserve_series)
        if kind == "call":
            name = node[1]
            args = [self.eval(arg, offset, preserve_series=True) for arg in node[2]]
            func = self.functions.get(name)
            if not func:
                raise ValueError(f"Unknown function: {name}")
            value = func(*args)
            return self._resolve_value(value, offset, preserve_series)
        if kind == "index":
            base = self.eval(node[1], offset, preserve_series=True)
            if not isinstance(base, SeriesAccessor):
                raise ValueError("Indexing requires a series")
            index = int(self.eval(node[2], offset))
            return base.value_at(index + offset)
        if kind == "unary":
            op = node[1]
            val = self.eval(node[2], offset)
            if val is None:
                return None
            return val if op == "+" else -val
        if kind == "bin":
            op = node[1]
            left = self.eval(node[2], offset)
            right = self.eval(node[3], offset)
            return apply_binary(op, left, right)
        if kind == "cmp":
            op = node[1]
            left_node = node[2]
            right_node = node[3]
            return apply_comparison(op, left_node, right_node, self, offset)
        if kind == "and":
            return bool(self.eval(node[1], offset)) and bool(self.eval(node[2], offset))
        if kind == "or":
            return bool(self.eval(node[1], offset)) or bool(self.eval(node[2], offset))
        if kind == "not":
            return not bool(self.eval(node[1], offset))
        raise ValueError(f"Unknown node: {node}")

    def _resolve_value(self, value, offset: int, preserve_series: bool):
        if isinstance(value, SeriesAccessor):
            if preserve_series:
                return value
            return value.value_at(offset)
        return value


def apply_binary(op: str, left: float | None, right: float | None):
    if left is None or right is None:
        return None
    if op == "+":
        return left + right
    if op == "-":
        return left - right
    if op == "*":
        return left * right
    if op == "/":
        if right == 0:
            raise ValueError("Division by zero")
        return left / right
    raise ValueError(f"Unknown operator: {op}")


def apply_comparison(op: str, left_node, right_node, evaluator: ExpressionEvaluator, offset: int):
    op_upper = op.upper()
    if op_upper in {"CROSSOVER", "CROSSUNDER"}:
        left_now = evaluator.eval(left_node, offset)
        right_now = evaluator.eval(right_node, offset)
        left_prev = evaluator.eval(left_node, offset + 1)
        right_prev = evaluator.eval(right_node, offset + 1)
        if None in {left_now, right_now, left_prev, right_prev}:
            return False
        if op_upper == "CROSSOVER":
            return left_now > right_now and left_prev <= right_prev
        return left_now < right_now and left_prev >= right_prev

    left = evaluator.eval(left_node, offset)
    right = evaluator.eval(right_node, offset)
    if left is None or right is None:
        return False

    if op_upper in {">", "GT", "ABOVE"}:
        return left > right
    if op_upper in {">=", "GTE"}:
        return left >= right
    if op_upper in {"<", "LT", "BELOW"}:
        return left < right
    if op_upper in {"<=", "LTE"}:
        return left <= right
    if op_upper in {"==", "EQ"}:
        return left == right
    if op_upper in {"!=", "NE"}:
        return left != right
    raise ValueError(f"Unknown comparison: {op}")


def parse_expression(expr: str):
    lexer = Lexer(expr)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    return parser.parse()


def evaluate_expression(expr: str, context: dict[str, Any], functions: dict[str, Callable]):
    tree = parse_expression(expr)
    evaluator = ExpressionEvaluator(context, functions)
    return evaluator.eval(tree, offset=0)


def evaluate_condition(condition: dict, lookup: Callable[[str], float | None]):
    if "all" in condition:
        return all(evaluate_condition(item, lookup) for item in condition["all"])
    if "any" in condition:
        return any(evaluate_condition(item, lookup) for item in condition["any"])
    if "not" in condition:
        return not evaluate_condition(condition["not"], lookup)

    op = condition["op"]
    left = lookup(condition["left"])
    right = lookup(condition["right"])

    if isinstance(left, SeriesAccessor):
        left = left.value_at(0)
    if isinstance(right, SeriesAccessor):
        right = right.value_at(0)

    if left is None or right is None:
        return False

    if op == "gt":
        return left > right
    if op == "gte":
        return left >= right
    if op == "lt":
        return left < right
    if op == "lte":
        return left <= right
    if op == "eq":
        return left == right
    if op == "ne":
        return left != right
    if op in {"crosses_above", "crossover"}:
        return False
    if op in {"crosses_below", "crossunder"}:
        return False

    raise ValueError(f"Unsupported operator: {op}")


def build_state_key(decision: str, action: str, rule_ids: list[str], reasons: list[dict[str, str]]):
    ids = sorted(rule_ids)
    ids_part = ",".join(ids) if ids else "NONE"
    reason_codes = sorted(reasons, key=lambda r: (r.get("code", ""), r.get("source", "")))
    normalized = [
        {key: value for key, value in reason.items() if key in {"code", "source"}}
        for reason in reason_codes
    ]
    import hashlib
    import json
    import base64

    payload = json.dumps(normalized, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    reason_hash = base64.b32encode(digest).decode("utf-8")[:8]
    return f"{decision}_{action}_{ids_part}_{reason_hash}"


def evaluate_rule_plan(
    rule_plan: dict,
    context: dict[str, Any],
    functions: dict[str, Callable],
    position_state: str,
) -> EvaluationResult:
    reasons: list[dict[str, str]] = []
    triggered_ids: list[str] = []

    if position_state not in {"flat", "holding"}:
        raise ValueError("position_state must be flat or holding")

    entry_rules = rule_plan.get("entry_rules", [])
    exit_rules = rule_plan.get("exit_rules", {})

    if position_state == "flat":
        matching_rules = []
        for rule in entry_rules:
            constraints_ok = True
            constraints = rule.get("constraints", [])
            for constraint in constraints:
                if not evaluate_condition(constraint, lambda name: context.get(name)):
                    constraints_ok = False
                    break
            constraints_expr = rule.get("constraints_expr", [])
            for expr in constraints_expr:
                if not evaluate_expression(expr, context, functions):
                    constraints_ok = False
                    break

            expr = rule.get("condition_expr")
            if expr:
                if constraints_ok and evaluate_expression(expr, context, functions):
                    matching_rules.append(rule)
            else:
                condition = rule.get("condition")
                if constraints_ok and condition and evaluate_condition(
                    condition, lambda name: context.get(name)
                ):
                    matching_rules.append(rule)

        if matching_rules:
            matching_rules.sort(key=lambda r: r.get("priority", 999999))
            chosen = matching_rules[0]
            triggered_ids.append(chosen.get("id", "ENTRY"))
            reasons.append({"code": "ENTRY_TRIGGERED", "source": chosen.get("id", "")})
            decision = "ALLOW"
            action = "BUY"
            state_key = build_state_key(decision, action, triggered_ids, reasons)
            return EvaluationResult(decision, action, state_key, reasons)

        reasons.append({"code": "ENTRY_CONDITION_NOT_MET"})
        decision = "BLOCK"
        action = "NONE"
        state_key = build_state_key(decision, action, triggered_ids, reasons)
        return EvaluationResult(decision, action, state_key, reasons)

    exit_conditions = exit_rules.get("conditions", [])
    for rule in exit_conditions:
        expr = rule.get("condition_expr")
        if expr:
            if evaluate_expression(expr, context, functions):
                triggered_ids.append(rule.get("id", "EXIT"))
        else:
            condition = rule.get("condition")
            if condition and evaluate_condition(condition, lambda name: context.get(name)):
                triggered_ids.append(rule.get("id", "EXIT"))

    if triggered_ids:
        reasons.append({"code": "EXIT_TRIGGERED", "source": triggered_ids[0]})
        decision = "ALLOW"
        action = "SELL"
        state_key = build_state_key(decision, action, triggered_ids, reasons)
        return EvaluationResult(decision, action, state_key, reasons)

    reasons.append({"code": "EXIT_CONDITION_NOT_MET"})
    decision = "BLOCK"
    action = "NONE"
    state_key = build_state_key(decision, action, triggered_ids, reasons)
    return EvaluationResult(decision, action, state_key, reasons)


def evaluate_with_bars(
    rule_plan: dict,
    bars: list[models.DailyBar],
    indicators: list[models.IndicatorDef],
    position_state: str,
    risk_context: dict[str, Any] | None = None,
    current_price: float | None = None,
):
    context = build_series_context(bars, indicators, current_price=current_price)
    if risk_context:
        for key, value in risk_context.items():
            context[key] = value
    functions = build_functions(bars)
    return evaluate_rule_plan(rule_plan, context, functions, position_state)
