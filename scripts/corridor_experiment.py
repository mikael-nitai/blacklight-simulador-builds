"""Exploratory bounded-corridor rerun of the open-field kiter scenario."""

from dataclasses import asdict, replace
from hashlib import sha256
import json
from math import sqrt
from pathlib import Path
from blacklight.results_io import write_new_text
import sys

from blacklight.audit import audit_log
from blacklight.engine import Profile, blacklight_profile
from blacklight.experiment import scenarios
from blacklight.policies import (HAMMER, KITER,
                                 SHIELD_HAMMER_REACTIVE,
                                 SHIELD_BLADE_HAMMER_REACTIVE)
from experimental.corridor import CorridorDuel
from experimental.corridor_audit import audit_corridor


ROOT = Path(__file__).resolve().parents[1]
POLICIES = (HAMMER, SHIELD_HAMMER_REACTIVE,
            SHIELD_BLADE_HAMMER_REACTIVE)
STAGES = {"dev": 1000, "description": 5000}


def gunners() -> tuple[tuple[str, Profile], ...]:
    ammo = next(s.opponent for s in scenarios() if s.id == "gunner_kiter")
    return (("C1_rank3_ammo", ammo),
            ("C2_rank4_nonammo",
             replace(ammo, rank=4, ranged_is_ammunition=False)))


def profile_record(profile: Profile) -> dict:
    row = asdict(profile)
    for name in ("powers", "traits", "weapons"):
        row[name] = sorted(row[name])
    return row


def seed_for(stage: str, length: int, opponent: str,
             policy: str, index: int) -> int:
    value = f"blacklight-corridor-pool-v2|{stage}|{length}|{opponent}|{policy}|{index}"
    return int.from_bytes(sha256(value.encode()).digest()[:8], "big")


def wilson(k: int, n: int) -> tuple[float, float]:
    z = 1.959963984540054
    p = k / n
    scale = 1 + z * z / n
    middle = (p + z * z / (2 * n)) / scale
    width = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / scale
    return middle - width, middle + width


def hashes() -> dict[str, str]:
    files = [ROOT / name for name in (
        "CORRIDOR_SPEC.md", "CORRIDOR_POOL_V2_ADDENDUM.md",
        "DAMAGE_POOL_RULING.md", "FAST_STRIKES_RULING.md",
        "RULES_AUDIT.md", "CHARACTER_AUDIT.md",
        "scripts/corridor_experiment.py", "experimental/corridor.py",
        "experimental/corridor_audit.py")]
    files.extend(sorted((ROOT / "blacklight").glob("*.py")))
    files.extend(sorted((ROOT / 'combatants').glob('*.py')))
    return {str(path.relative_to(ROOT)).replace("\\", "/"):
            sha256(path.read_bytes()).hexdigest() for path in files}


def run_cell(stage: str, length: int, opponent_id: str,
             opponent: Profile, policy: object, n: int) -> dict:
    profiles = (blacklight_profile(), opponent)
    outcomes = {"win": 0, "loss": 0, "inconclusive": 0, "draw": 0}
    wall_count = 0
    contact_count = 0
    round_sum = 0
    audited = 0
    for index in range(n):
        audit = stage == "description" and index % 100 == 0
        duel = CorridorDuel(profiles, (policy, KITER),
                            seed=seed_for(stage, length, opponent_id,
                                          policy.name, index),
                            length=length, initial_positions=(0, 8),
                            audit=audit)
        result = duel.run()
        if audit:
            issues = audit_log(
                result.log,
                {p.name: p.max_health for p in profiles},
                {p.name: p.max_focus for p in profiles})
            issues += audit_corridor(
                result.log, tuple(p.name for p in profiles),
                initial_positions=(0, 8), length=length,
                final_positions=tuple(duel.positions),
                wall_reached=duel.wall_reached,
                contact_occurred=duel.contact_occurred)
            if issues:
                raise RuntimeError(
                    f"Corridor audit failed {length} {opponent_id} {policy.name} {index}: {issues}")
            audited += 1
        if result.outcome == "inconclusive":
            outcome = "inconclusive"
        elif result.outcome == "draw":
            outcome = "draw"
        elif result.winner == profiles[0].name:
            outcome = "win"
        else:
            outcome = "loss"
        outcomes[outcome] += 1
        wall_count += duel.wall_reached
        contact_count += duel.contact_occurred
        round_sum += result.rounds
    return {"stage": stage, "length": length,
            "opponent": opponent_id, "policy": policy.name,
            "n": n, "outcomes": outcomes,
            "rates": {key: {"estimate": value / n,
                            "wilson95": wilson(value, n)}
                      for key, value in outcomes.items()},
            "wall_reached": wall_count,
            "contact_occurred": contact_count,
            "mean_rounds": round_sum / n,
            "full_logs_audited": audited}


def main() -> None:
    from argparse import ArgumentParser
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=STAGES, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--historical-rules', action='store_true')
    args = parser.parse_args()
    if not args.historical_rules:
        parser.error('Corridor Fast Strikes still uses the historical contract; pass --historical-rules explicitly')
    output = args.output or ROOT / 'results' / f'corridor_pool_v2_{args.stage}_summary.json'
    if output.exists():
        parser.error('Output already exists; use --output with a new versioned filename')
    n = STAGES[args.stage]
    rows = []
    configured = gunners()
    for length in (12, 20):
        for opponent_id, opponent in configured:
            for policy in POLICIES:
                row = run_cell(args.stage, length, opponent_id,
                               opponent, policy, n)
                rows.append(row)
                print(f"{args.stage} L{length} {opponent_id} {policy.name}: "
                      f"{row['outcomes']}, wall={row['wall_reached']}",
                      flush=True)
    payload = {
        "schema": "blacklight-bounded-corridor-pool-v2",
        "damage_model": "literal_marvel_pool_v2",
        "stage": args.stage, "n_per_cell": n,
        "seed_formula": "first 8 bytes SHA-256 of blacklight-corridor-pool-v2|stage|length|opponent|policy|index",
        "damage_seed_formula": "duel seed XOR 0xD6162026; separate Python Random stream",
        "source_sha256": hashes(), "python": sys.version,
        "initial_positions": [0, 8], "lengths": [12, 20],
        "opponents": [{"id": name, "profile": profile_record(profile)}
                      for name, profile in configured],
        "policies": [asdict(p) for p in POLICIES],
        "opponent_policy": asdict(KITER), "rows": rows,
    }
    write_new_text(output, json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
