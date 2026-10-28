"""Run reserved controlled scenario variations for preselected finalists."""

from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import sys

from blacklight.experiment import ROOT, Scenario, run_cell, scenarios, source_hashes, strategies
from blacklight.results_io import historical_output, require_unchanged_sources, write_new_text


def holdout_scenarios() -> tuple[Scenario, ...]:
    base = {scenario.id: scenario for scenario in scenarios()}
    return (
        replace(base["mirror_hammer"], id="mirror_hammer_d8", distance=8),
        replace(base["mirror_shield"], id="mirror_shield_r6",
                opponent=replace(base["mirror_shield"].opponent,
                                 resilience=6, max_health=180)),
        replace(base["gunner_kiter"], id="gunner_kiter_d1", distance=1),
    )


def execution_sources() -> dict[str, str]:
    sources = source_hashes()
    for name in ('scripts/holdout.py', 'HOLDOUT_SPEC.md'):
        sources[name] = sha256((ROOT / name).read_bytes()).hexdigest()
    return sources


def main() -> None:
    output = historical_output(__doc__)
    sources = execution_sources()
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
    require_unchanged_sources(sources, execution_sources())
    payload = {
        "schema": "blacklight-holdout-v1",
        "n_per_cell": 10000,
        "damage_model": "literal_marvel_pool_v2",
        "table_ruleset": "literal_marvel_pool_v2",
        "seed_formula": "first 8 bytes SHA-256 of blacklight-pool-v2|holdout|scenario|strategy|index",
        "python": sys.version,
        "source_sha256": sources,
        "holdout_script_sha256": sources['scripts/holdout.py'],
        "holdout_spec_sha256": sources['HOLDOUT_SPEC.md'],
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
    write_new_text(output, json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
