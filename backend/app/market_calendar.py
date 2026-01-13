import json
from pathlib import Path


def load_holidays(path: str | None) -> set[str]:
    if not path:
        return set()

    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Market calendar file not found: {file_path}")

    if file_path.suffix.lower() == ".json":
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        return set(payload.get("holidays", []))

    if file_path.suffix.lower() == ".csv":
        lines = file_path.read_text(encoding="utf-8").splitlines()
        return {line.strip() for line in lines if line.strip() and not line.startswith("#")}

    raise ValueError("Market calendar must be .json or .csv")
