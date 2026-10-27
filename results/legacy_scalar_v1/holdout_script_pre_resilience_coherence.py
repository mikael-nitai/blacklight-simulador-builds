"""Run reserved controlled scenario variations for preselected finalists."""

from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import sys

from blacklight.experiment import ROOT, Scenario, run_cell, scenarios, source_hashes, strategies


def holdout_scenarios() -> tuple[Scenario, ...]:
    base = {scenario.id: scenario for scenario in scenarios()}
    return (
        replace(base["mirror_hammer"], id="mirror_hammer_d8", distance=8),
        replace(base["mirror_shield"], id="mirror_shield_h200",
                opponent=replace(base["mirror_shield"].opponent,
                                 max_health=200)),
        replace(base["gunner_kiter"], id="gunner_kiter_d1", distance=1),
    )


def main() -> None:
    keep = {"bare_attack", "hammer", "shield_hammer_reactive",
            "hammer_heal_t75_s15", "shield_hammer_endturn"}
    finalists = tuple(policy for policy in strategies() if policy.id in keep)
    rows = []
    for scenario in holdout_scenarios():
        for strategy in finalists:
            row = run_cell("holdout", scenario, strategy, 10000)
            rows.append(row)
            print(f"holdout {scenario.id} {strategy.id}: "
                  f"{row['outcomes']['win']}/10000 wins", flush=True)
    script = Path(__file__)
    spec = ROOT / "HOLDOUT_SPEC.md"
    payload = {
        "schema": "blacklight-holdout-v1",
        "n_per_cell": 10000,
        "seed_formula": "first 8 bytes SHA-256 of blacklight-v1|holdout|scenario|strategy|index",
        "python": sys.version,
        "source_sha256": source_hashes(),
        "holdout_script_sha256": sha256(script.read_bytes()).hexdigest(),
        "holdout_spec_sha256": sha256(spec.read_bytes()).hexdigest(),
        "scenarios": [
            {"id": s.id, "distance": s.distance,
             "opponent": {"name": s.opponent.name, "rank": s.opponent.rank,
                          "max_health": s.opponent.max_health,
                          "max_focus": s.opponent.max_focus,
                          "melee": s.opponent.melee, "agility": s.opponent.agility,
                          "resilience": s.opponent.resilience,
                          "run_speed": s.opponent.run_speed},
             "opponent_policy": s.policy.name}
            for s in holdout_scenarios()],
        "rows": rows,
    }
    output = ROOT / "results" / "holdout_summary.json"
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                      encoding="utf-8")


if __name__ == "__main__":
    main()
