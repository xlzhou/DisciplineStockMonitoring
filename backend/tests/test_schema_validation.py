from app.validation import validate_rule_plan


def test_rule_plan_example_valid(rule_plan_payload):
    errors = validate_rule_plan(rule_plan_payload)
    assert errors == []


def test_rule_plan_invalid_missing_field(rule_plan_payload):
    payload = dict(rule_plan_payload)
    payload.pop("ticker", None)
    errors = validate_rule_plan(payload)
    assert errors
