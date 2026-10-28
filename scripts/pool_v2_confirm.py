"""Run preregistered literal-damage finalists on replication and holdout."""

from argparse import ArgumentParser
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys

from blacklight.engine import Profile
from blacklight.experiment import ROOT, Scenario, run_cell, scenarios, source_hashes, strategies
from blacklight.policies import HAMMER, KITER
from blacklight.results_io import require_new_output, require_unchanged_sources, write_new_text


FINALISTS = (
    "bare_attack", "hammer", "blade_hammer_fast",
    "shield_blade_reactive", "shield_hammer_reactive",
    "shield_blade_hammer_reactive",
)


def holdout_scenarios() -> tuple[Scenario, ...]:
    bruiser = Profile(
        "Rank4 Bruiser", rank=4, max_health=180, max_focus=60,
        melee=7, agility=2, resilience=6, vigilance=3,
        melee_defense=17, agility_defense=12, run_speed=5,
        melee_bonus=2, powers=frozenset({"mighty"}),
        weapons=frozenset({"hammer"}),
    )
    energy_kiter = Profile(
        "Rank4 Energy Kiter", rank=4, max_health=120, max_focus=60,
        melee=3, agility=7, resilience=4, vigilance=3,
        melee_defense=13, agility_defense=17, run_speed=6,
        ranged_range=10, ranged_is_ammunition=False,
    )
    return (
        Scenario("H1_rank4_bruiser", bruiser, HAMMER, 1),
        Scenario("H2_rank4_energy_kiter", energy_kiter, KITER, 8),
    )


def profile_record(profile: Profile) -> dict:
    row = asdict(profile)
    for key in ("powers", "traits", "weapons"):
        row[key] = sorted(row[key])
    return row


def execution_sources() -> dict[str, str]:
    spec = ROOT / 'POOL_V2_CONFIRM_SPEC.md'
    script = Path(__file__).resolve()
    sources = source_hashes()
    sources[spec.relative_to(ROOT).as_posix()] = sha256(spec.read_bytes()).hexdigest()
    sources[script.relative_to(ROOT).as_posix()] = sha256(script.read_bytes()).hexdigest()
    return sources


def execute(stage: str, n: int, output: Path) -> dict:
    require_new_output(output)
    if stage not in ("confirm_v2", "holdout_v2") or n < 1:
        raise ValueError("Unknown stage or invalid sample count")
    sources = execution_sources()
    configured = scenarios() if stage == "confirm_v2" else holdout_scenarios()
    candidates = {s.id: s for s in strategies()}
    rows = []
    for scenario in configured:
        for strategy_id in FINALISTS:
            strategy = candidates[strategy_id]
            row = run_cell(stage, scenario, strategy, n)
            rows.append(row)
            print(f"{stage} {scenario.id} {strategy_id}: {row['outcomes']}",
                  flush=True)
    require_unchanged_sources(sources, execution_sources())
    payload = {
        "schema": "blacklight-finalists-pool-v2",
        "damage_model": "literal_marvel_pool_v2",
        "table_ruleset": "literal_marvel_pool_v2",
        "stage": stage, "n_per_cell": n,
        "seed_formula": "first 8 bytes SHA-256 of blacklight-pool-v2|stage|scenario|strategy|index",
        "damage_seed_formula": "duel seed XOR 0xD6162026; separate Python Random stream",
        "source_sha256": sources, "python": sys.version,
        "finalists": list(FINALISTS),
        "scenarios": [{"id": s.id, "opponent": profile_record(s.opponent),
                       "distance": s.distance, "opponent_policy": asdict(s.policy)}
                      for s in configured],
        "rows": rows,
        "limitations": ["synthetic opponents", "two actors", "open field",
                        "no Karma", "no numeric limb effect"],
    }
    write_new_text(output, json.dumps(payload, indent=2, ensure_ascii=False))
    return payload


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("confirm_v2", "holdout_v2"),
                        required=True)
    parser.add_argument("--n", type=int, default=10_000)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument('--historical-rules', action='store_true')
    args = parser.parse_args()
    if not args.historical_rules:
        parser.error('This experiment uses the historical single-check Fast rules; pass --historical-rules explicitly')
    if args.output.exists():
        parser.error('Output already exists; choose a new versioned filename')
    execute(args.stage, args.n, args.output)


if __name__ == "__main__":
    main()
