"""Print compact Markdown tables directly from saved, hash-checked results."""

import json
from pathlib import Path

from blacklight.experiment import ROOT, scenarios, source_hashes, strategies


def load(name: str) -> dict:
    data = json.loads((ROOT / "results" / name).read_text(encoding="utf-8"))
    if data["source_sha256"] != source_hashes():
        raise RuntimeError(f"stale source hashes: {name}")
    return data


def main() -> None:
    data = load("confirm_summary.json")
    by_key = {(r["scenario"], r["strategy"]): r for r in data["rows"]}
    print("| Política | S1 vitória % [IC95] | S2 | S3 | S4 |")
    print("|---|---:|---:|---:|---:|")
    labels = {"bare_attack": "P1", "stance_bare": "P2", "hammer": "P3",
              "blade_hammer_fast": "P4", "hammer_heal": "P5",
              "shield_blade_reactive": "P6", "hybrid": "P7",
              "shield_hammer_reactive": "P8",
              "hammer_heal_t75_s15": "P9",
              "shield_hammer_endturn": "P10"}
    for policy in sorted(strategies(), key=lambda p: int(labels[p.id][1:])):
        cells = []
        for scenario in scenarios():
            row = by_key[scenario.id, policy.id]
            lo, hi = row["win_ci95_wilson"]
            cells.append(f"{100 * row['win_rate']:.1f} "
                         f"[{100 * lo:.1f}; {100 * hi:.1f}]")
        print(f"| {labels[policy.id]} `{policy.id}` | " + " | ".join(cells) + " |")
    print("\nS4 win/loss/inconclusive")
    for policy in sorted(strategies(), key=lambda p: int(labels[p.id][1:])):
        print(labels[policy.id], by_key["gunner_kiter", policy.id]["outcomes"])


if __name__ == "__main__":
    main()
