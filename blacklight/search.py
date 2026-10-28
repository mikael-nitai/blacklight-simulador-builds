"""Pre-registered exploratory grid for Do This All Day thresholds."""

from dataclasses import replace
import json
from pathlib import Path

from .experiment import ROOT, Strategy, run_cell, scenarios, source_hashes
from .policies import HAMMER
from .results_io import historical_output, write_new_text


def main() -> None:
    output = historical_output(__doc__)
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
               "damage_model": "literal_marvel_pool_v2",
               "table_ruleset": "literal_marvel_pool_v2",
               "seed_formula": "first 8 bytes SHA-256 of blacklight-pool-v2|stage|scenario|strategy|index",
               "selection_rule": "maximin S1-S3 wins; tie lower mean Focus spent",
               "source_sha256": source_hashes(), "rankings": rankings,
               "rows": rows, "selected": rankings[0]["strategy"]}
    write_new_text(output, json.dumps(payload, ensure_ascii=False, indent=2))
    print(*rankings, sep="\n")


if __name__ == "__main__":
    main()
