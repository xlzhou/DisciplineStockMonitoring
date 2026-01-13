import json
from pathlib import Path

from jsonschema import Draft7Validator

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "rule_plan.schema.json"


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_rule_plan(payload: dict) -> list[str]:
    schema = load_schema()
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.path))
    messages = []
    for error in errors:
        path = ".".join(str(p) for p in error.path) or "<root>"
        messages.append(f"{path}: {error.message}")
    return messages
