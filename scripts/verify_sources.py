"""Check recorded source SHA-256 values in result JSON files."""

from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def verify(include_historical: bool = False) -> tuple[int, list[str]]:
    checked = 0
    issues: list[str] = []
    for result in sorted((ROOT / "results").glob("*.json")):
        if not include_historical and (
                "pre_" in result.name or result.name.startswith("invalid_")):
            continue
        payload = json.loads(result.read_text(encoding="utf-8"))
        sources = payload.get("source_sha256")
        if not isinstance(sources, dict):
            continue
        checked += 1
        for source, expected in sources.items():
            path = ROOT / source
            actual = sha256(path.read_bytes()).hexdigest() if path.is_file() else None
            if actual != expected:
                issues.append(f"{result.name}: {source} SHA-256 mismatch")
    return checked, issues


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--include-historical", action="store_true")
    args = parser.parse_args()
    checked, issues = verify(args.include_historical)
    print(f"Checked {checked} result JSONs; {len(issues)} source mismatches")
    for issue in issues:
        print(issue)
    if issues:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
