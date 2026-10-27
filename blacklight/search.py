"""Pre-registered exploratory grid for Do This All Day thresholds."""

from dataclasses import replace
import json
from pathlib import Path

from .experiment import ROOT, Strategy, run_cell, scenarios, source_hashes
from .policies import HAMMER


def main() -> None:
    selected_scenarios = [s for s in scenarios() if s.id != "gunner_kiter"]
    candidates = [
        Strategy(f"hammer_heal_t{threshold}_s{spend}",
                 replace(HAMMER, name=f"hammer_heal_t{threshold}_s{spend}",
                         heal_missing=threshold, heal_spend=spend))
        for threshold in (45, 60, 75) for spend in (10, 15)
    ]
    rows = [run_cell("heal_search", scenario, strategy, 1000)
            for strategy in candidates for scenario in selected_scenarios]
    rankings = []
    for candidate in candidates:
        block = [row for row in rows if row["strategy"] == candidate.id]
        rankings.append({
            "strategy": candidate.id,
            "worst_win_rate": min(row["win_rate"] for row in block),
            "mean_focus_spent": sum(row["metrics_all_starts"]["focus_spent"]["mean"]
                                    for row in block) / len(block),
            "win_rates": {row["scenario"]: row["win_rate"] for row in block},
        })
    rankings.sort(key=lambda row: (-row["worst_win_rate"],
                                   row["mean_focus_spent"], row["strategy"]))
    payload = {"stage": "heal_search", "n_per_cell": 1000,
               "selection_rule": "maximin S1-S3 wins; tie lower mean Focus spent",
               "source_sha256": source_hashes(), "rankings": rankings,
               "rows": rows, "selected": rankings[0]["strategy"]}
    output = ROOT / "results" / "heal_search.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(*rankings, sep="\n")


if __name__ == "__main__":
    main()
