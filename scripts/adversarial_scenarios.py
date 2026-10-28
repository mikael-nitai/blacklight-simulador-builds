"""Post-confirmation, explicitly exploratory adversarial stress tests."""

from dataclasses import asdict, replace
from hashlib import sha256
import json
from pathlib import Path
import sys

from blacklight.engine import Profile, blacklight_profile
from blacklight.experiment import ROOT, Scenario, run_cell, scenarios, source_hashes, strategies
from blacklight.policies import ATTACK, HAMMER, KITER
from blacklight.results_io import historical_output, require_unchanged_sources, write_new_text


def profile_record(profile: Profile) -> dict:
    record = asdict(profile)
    for key in ("powers", "traits", "weapons"):
        record[key] = sorted(record[key])
    return record


def adversarial_scenarios() -> tuple[Scenario, ...]:
    mirror = replace(blacklight_profile(), name="Enemy", rank=4)
    low = Profile("Enemy", rank=2, max_health=90, max_focus=60,
                  melee=4, agility=1, resilience=3, vigilance=2,
                  melee_defense=14, agility_defense=11, run_speed=5)
    gunner = next(s.opponent for s in scenarios() if s.id == "gunner_kiter")
    energy = replace(gunner, rank=4, ranged_is_ammunition=False)
    return (
        Scenario("rank4_hammer", mirror, HAMMER, 1),
        Scenario("rank2_brawler", low, ATTACK, 1),
        Scenario("rank4_nonammo_kiter", energy, KITER, 8),
    )


def execution_sources() -> dict[str, str]:
    sources = source_hashes()
    for name in ('scripts/adversarial_scenarios.py', 'ADVERSARIAL_SPEC.md'):
        sources[name] = sha256((ROOT / name).read_bytes()).hexdigest()
    return sources


def main() -> None:
    output = historical_output(__doc__)
    sources = execution_sources()
    keep = {"bare_attack", "hammer", "shield_hammer_reactive",
            "hammer_heal_t75_s15", "shield_hammer_endturn"}
    selected = tuple(s for s in strategies() if s.id in keep)
    rows = []
    for scenario in adversarial_scenarios():
        for strategy in selected:
            row = run_cell("adversarial", scenario, strategy, 5000)
            rows.append(row)
            print(f"adversarial {scenario.id} {strategy.id}: "
                  f"{row['outcomes']}", flush=True)
    require_unchanged_sources(sources, execution_sources())
    payload = {
        "schema": "blacklight-adversarial-v1", "n_per_cell": 5000,
        "damage_model": "literal_marvel_pool_v2",
        "table_ruleset": "literal_marvel_pool_v2",
        "seed_formula": "first 8 bytes SHA-256 of blacklight-pool-v2|adversarial|scenario|strategy|index",
        "source_sha256": sources,
        "script_sha256": sources['scripts/adversarial_scenarios.py'],
        "spec_sha256": sources['ADVERSARIAL_SPEC.md'],
        "python": sys.version,
        "scenarios": [{"id": s.id, "distance": s.distance,
                       "opponent": profile_record(s.opponent),
                       "opponent_policy": asdict(s.policy)}
                      for s in adversarial_scenarios()],
        "rows": rows,
    }
    write_new_text(output, json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
