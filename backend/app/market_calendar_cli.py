import argparse
from pathlib import Path

from .market_calendar import load_holidays


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a market calendar file.")
    parser.add_argument("path", help="Path to calendar file (.json or .csv)")
    args = parser.parse_args()

    path = Path(args.path)
    try:
        holidays = load_holidays(str(path))
    except Exception as exc:  # noqa: BLE001
        print(f"Invalid calendar: {exc}")
        return 1

    if not holidays:
        print("Calendar loaded, but no holidays found.")
        return 0

    sorted_days = sorted(holidays)
    print(f"Calendar OK: {len(sorted_days)} holidays")
    print("First:", sorted_days[0])
    print("Last:", sorted_days[-1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
