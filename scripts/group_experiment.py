"""Reproducible fixed-contact three-actor exploratory experiment."""

from dataclasses import asdict
from hashlib import sha256
import json
from math import sqrt
from pathlib import Path
from blacklight.results_io import require_unchanged_sources, write_new_text
import sys

from blacklight.engine import Profile, blacklight_profile
from experimental.group import GroupBattle
from experimental.group_audit import audit_group_result
from experimental.group_policies import (GROUP_ENEMY, GROUP_FAST,
                                         GROUP_HAMMER, GROUP_HAMMER_SHIELD)


ROOT = Path(__file__).resolve().parents[1]
POLICIES = (GROUP_HAMMER, GROUP_HAMMER_SHIELD, GROUP_FAST)
STAGES = (("dev", 1000), ("description", 10000))


def enemy(name: str, *, rank: int, melee: int,
          resilience: int) -> Profile:
    return Profile(name, rank, 30 * resilience, 60, melee, 1,
                   resilience, 2, 10 + melee, 11, 5)


def scenarios() -> tuple[tuple[str, tuple[Profile, Profile, Profile]], ...]:
    return (
        ("G1_two_rank2_brawlers",
         (blacklight_profile(), enemy("E1", rank=2, melee=4, resilience=3),
          enemy("E2", rank=2, melee=4, resilience=3))),
        ("G2_two_rank3_brawlers",
         (blacklight_profile(), enemy("E1", rank=3, melee=6, resilience=5),
          enemy("E2", rank=3, melee=6, resilience=5))),
    )


def seed_for(stage: str, scenario: str, policy: str, index: int) -> int:
    value = f"blacklight-group-pool-v2|{stage}|{scenario}|{policy}|{index}"
    return int.from_bytes(sha256(value.encode()).digest()[:8], "big")


def wilson(k: int, n: int) -> tuple[float, float]:
    z = 1.959963984540054
    p = k / n
    scale = 1 + z * z / n
    middle = (p + z * z / (2 * n)) / scale
    width = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / scale
    return middle - width, middle + width


def profile_record(profile: Profile) -> dict:
    row = asdict(profile)
    for name in ("powers", "traits", "weapons"):
        row[name] = sorted(row[name])
    return row


def hashes() -> dict[str, str]:
    files = [ROOT / "GROUP_EXPERIMENT_SPEC.md", ROOT / "GROUP_SPEC.md",
             ROOT / "GROUP_POOL_V2_ADDENDUM.md",
             ROOT / "DAMAGE_POOL_RULING.md", ROOT / "FAST_STRIKES_RULING.md",
             ROOT / "scripts" / "group_experiment.py"]
    files.extend(ROOT / "experimental" / name for name in (
        "__init__.py", "group.py", "group_audit.py",
        "group_policies.py", "multi_target.py"))
    files.extend(sorted((ROOT / "blacklight").glob("*.py")))
    files.extend(sorted((ROOT / 'combatants').glob('*.py')))
    files.extend(ROOT / name for name in ("RULES_AUDIT.md", "CHARACTER_AUDIT.md"))
    return {str(path.relative_to(ROOT)).replace("\\", "/"):
            sha256(path.read_bytes()).hexdigest() for path in files}


def run_cell(stage: str, scenario_id: str, profiles: tuple[Profile, ...],
             policy: object, n: int) -> dict:
    counts = {"win": 0, "loss": 0, "inconclusive": 0}
    rounds_sum = 0
    bonus_count = 0
    audited = 0
    for index in range(n):
        audit = stage == "description" and index % 100 == 0
        result = GroupBattle(profiles, (policy, GROUP_ENEMY, GROUP_ENEMY),
                             seed=seed_for(stage, scenario_id, policy.name, index),
                             max_rounds=30, audit=audit).run()
        if audit:
            issues = audit_group_result(result, profiles)
            if issues:
                raise RuntimeError(f"Group audit failed: {scenario_id} {policy.name} {index}: {issues}")
            audited += 1
        counts[result.outcome] += 1
        rounds_sum += result.rounds
        bonus_count += result.bonus_round_occurred
    return {"stage": stage, "scenario": scenario_id, "policy": policy.name,
            "n": n, "outcomes": counts,
            "rates": {key: {"estimate": value / n,
                            "wilson95": wilson(value, n)}
                      for key, value in counts.items()},
            "mean_rounds": rounds_sum / n,
            "bonus_round_fraction": bonus_count / n,
            "full_logs_audited": audited}


def main() -> None:
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("--stage", choices=("dev", "description"), required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--historical-rules', action='store_true')
    args = parser.parse_args()
    if not args.historical_rules:
        parser.error('Group Fast Strikes still uses the historical contract; pass --historical-rules explicitly')
    output = args.output or ROOT / 'results' / f'group_pool_v2_{args.stage}_summary.json'
    if output.exists():
        parser.error('Output already exists; use --output with a new versioned filename')
    sources = hashes()
    n = dict(STAGES)[args.stage]
    rows = []
    configured = scenarios()
    for scenario_id, profiles in configured:
        for policy in POLICIES:
            row = run_cell(args.stage, scenario_id, profiles, policy, n)
            rows.append(row)
            print(f"{args.stage} {scenario_id} {policy.name}: {row['outcomes']}",
                  flush=True)
    require_unchanged_sources(sources, hashes())
    payload = {
        "schema": "blacklight-fixed-contact-group-pool-v2",
        "damage_model": "literal_marvel_pool_v2",
        "table_ruleset": "literal_marvel_pool_v2",
        "stage": args.stage,
        "n_per_cell": n,
        "seed_formula": "first 8 bytes SHA-256 of blacklight-group-pool-v2|stage|scenario|policy|index",
        "damage_seed_formula": "battle seed XOR 0xD6162026; separate Python Random stream",
        "source_sha256": sources,
        "python": sys.version,
        "scenarios": [{"id": name,
                       "profiles": [profile_record(p) for p in profiles]}
                      for name, profiles in configured],
        "policies": [asdict(policy) for policy in POLICIES],
        "rows": rows,
    }
    write_new_text(output, json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
