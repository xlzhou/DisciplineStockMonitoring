#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"File not found: {path}")
        sys.exit(2)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON in {path}: {exc}")
        sys.exit(2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a rule plan against the JSON schema.")
    parser.add_argument(
        "--schema",
        default="rule_plan.schema.json",
        help="Path to rule plan JSON schema",
    )
    parser.add_argument(
        "--plan",
        default="rule_plan.example.json",
        help="Path to rule plan JSON file",
    )
    args = parser.parse_args()

    try:
        from jsonschema import Draft7Validator
    except ImportError:
        print("Missing dependency: jsonschema")
        print("Install with: python3 -m pip install jsonschema")
        return 2

    schema_path = Path(args.schema)
    plan_path = Path(args.plan)

    schema = load_json(schema_path)
    plan = load_json(plan_path)

    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(plan), key=lambda e: list(e.path))

    if not errors:
        print("OK: rule plan is valid.")
        return 0

    print("Invalid rule plan:")
    for error in errors:
        path = ".".join(str(p) for p in error.path) or "<root>"
        print(f"- {path}: {error.message}")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
