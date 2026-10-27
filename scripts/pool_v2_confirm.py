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


def execute(stage: str, n: int, output: Path) -> dict:
    if stage not in ("confirm_v2", "holdout_v2") or n < 1:
        raise ValueError("Unknown stage or invalid sample count")
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
    spec = ROOT / "POOL_V2_CONFIRM_SPEC.md"
    script = Path(__file__).resolve()
    sources = source_hashes()
    sources[str(spec.relative_to(ROOT))] = sha256(spec.read_bytes()).hexdigest()
    sources[str(script.relative_to(ROOT))] = sha256(script.read_bytes()).hexdigest()
    payload = {
        "schema": "blacklight-finalists-pool-v2",
        "damage_model": "literal_marvel_pool_v2",
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
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                      encoding="utf-8")
    return payload


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("confirm_v2", "holdout_v2"),
                        required=True)
    parser.add_argument("--n", type=int, default=10_000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    execute(args.stage, args.n, args.output)


if __name__ == "__main__":
    main()
