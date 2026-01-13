import math

from app.rule_engine import evaluate_expression
from app.series import SeriesAccessor


def test_expression_arithmetic_and_offsets():
    context = {
        "Close": SeriesAccessor([110.0, 100.0]),
    }
    functions = {}
    expr = "(Close / Close[1] - 1) * 100"
    result = evaluate_expression(expr, context, functions)
    assert round(result, 2) == 10.0


def test_expression_change_diff():
    context = {
        "Close": SeriesAccessor([110.0, 100.0]),
    }

    def change(series):
        if isinstance(series, SeriesAccessor):
            series = series
        current = series.value_at(0)
        previous = series.value_at(1)
        if current is None or previous is None:
            return None
        return current - previous

    def diff(a, b):
        if isinstance(a, SeriesAccessor):
            a = a.value_at(0)
        if isinstance(b, SeriesAccessor):
            b = b.value_at(0)
        if a is None or b is None:
            return None
        return a - b

    functions = {
        "change": change,
        "diff": diff,
    }
    assert evaluate_expression("change(Close)", context, functions) == 10.0
    assert evaluate_expression("diff(Close, Close[1])", context, functions) == 10.0


def test_expression_crossover():
    context = {
        "Fast": SeriesAccessor([105.0, 100.0]),
        "Slow": SeriesAccessor([102.0, 101.0]),
    }
    functions = {}
    assert evaluate_expression("Fast crossover Slow", context, functions) is True


def test_expression_highest_lowest():
    context = {
        "Close": SeriesAccessor([5.0, 4.0, 6.0, 3.0]),
    }
    functions = {
        "highest": lambda series, n: max(series.values[: int(n)]),
        "lowest": lambda series, n: min(series.values[: int(n)]),
    }
    assert evaluate_expression("highest(Close, 3)", context, functions) == 6.0
    assert evaluate_expression("lowest(Close, 3)", context, functions) == 4.0


def test_expression_division_by_zero():
    context = {
        "Close": SeriesAccessor([10.0, 0.0]),
    }
    functions = {}
    try:
        evaluate_expression("Close / Close[1]", context, functions)
    except ValueError as exc:
        assert "Division by zero" in str(exc)
    else:
        raise AssertionError("Expected division by zero error")
