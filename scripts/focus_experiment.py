"""Exploratory fixed-contact Mental Punch duel, with separate shield variants."""

from dataclasses import asdict
from hashlib import sha256
import json
from math import sqrt
from pathlib import Path
import sys

from blacklight.engine import Profile, blacklight_profile
from experimental.focus_audit import audit_focus_duel
from experimental.focus_duel import FocusDuel, STRATEGIES


ROOT = Path(__file__).resolve().parents[1]
STAGES = {"dev": 1000, "description": 5000}


def mentalist(rank: int) -> Profile:
    return Profile("Mentalist", rank, 150, 60, 6, 1, 5, 2,
                   16, 11, 5, powers=frozenset({"mental_punch"}))


def profile_record(profile: Profile) -> dict:
    row = asdict(profile)
    for name in ("powers", "traits", "weapons"):
        row[name] = sorted(row[name])
    return row


def seed_for(stage: str, scenario: str, variant: str,
             strategy: str, index: int) -> int:
    value = f"blacklight-focus-pool-v2|{stage}|{scenario}|{variant}|{strategy}|{index}"
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
        "FOCUS_SPEC.md", "FOCUS_DUEL_SPEC.md", "RULES_AUDIT.md",
        "CHARACTER_AUDIT.md", "FOCUS_RULING.md",
        "DAMAGE_POOL_RULING.md", "DAMAGE_POOL_V2_SPEC.md",
        "scripts/focus_experiment.py")]
    files.extend(sorted((ROOT / "experimental").glob("focus_*.py")))
    files.extend(sorted((ROOT / "blacklight").glob("*.py")))
    return {str(path.relative_to(ROOT)).replace("\\", "/"):
            sha256(path.read_bytes()).hexdigest() for path in files}


def run_cell(stage: str, scenario: str, profiles: tuple[Profile, Profile],
             variant: str, strategy: str, n: int) -> dict:
    reduction = 0 if variant == "F0" else 2
    counts = {"win": 0, "loss": 0, "inconclusive": 0}
    demoralized = 0
    shattered = 0
    focus_sum = 0
    rounds_sum = 0
    audited = 0
    for index in range(n):
        audit = stage == "description" and index % 100 == 0
        result = FocusDuel(*profiles, strategy=strategy,
                           shield_focus_reduction=reduction,
                           seed=seed_for(stage, scenario, variant,
                                         strategy, index),
                           audit=audit).run()
        if audit:
            issues = audit_focus_duel(result, profiles, reduction)
            if issues:
                raise RuntimeError(
                    f"Focus audit failed {scenario} {variant} {strategy} {index}: {issues}")
            audited += 1
        counts[result.outcome] += 1
        demoralized += result.ever_demoralized
        shattered += result.final_focus[0] <= -profiles[0].max_focus
        focus_sum += result.final_focus[0]
        rounds_sum += result.rounds
    return {"stage": stage, "scenario": scenario, "variant": variant,
            "strategy": strategy, "n": n, "outcomes": counts,
            "rates": {key: {"estimate": value / n,
                            "wilson95": wilson(value, n)}
                      for key, value in counts.items()},
            "ever_demoralized": demoralized,
            "shattered": shattered,
            "mean_final_focus": focus_sum / n,
            "mean_rounds": rounds_sum / n,
            "full_logs_audited": audited}


def main() -> None:
    from argparse import ArgumentParser
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=STAGES, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = args.output or ROOT / 'results' / f'focus_pool_v2_{args.stage}_summary.json'
    if output.exists():
        parser.error('Output already exists; use --output with a new versioned filename')
    n = STAGES[args.stage]
    configured = tuple((f"M{rank}",
                        (blacklight_profile(), mentalist(rank)))
                       for rank in (3, 4))
    rows = []
    for scenario, profiles in configured:
        for variant in ("F0", "F2"):
            for strategy in STRATEGIES:
                row = run_cell(args.stage, scenario, profiles,
                               variant, strategy, n)
                rows.append(row)
                print(f"{args.stage} {scenario} {variant} {strategy}: "
                      f"{row['outcomes']}, demoralized={row['ever_demoralized']}",
                      flush=True)
    payload = {
        "schema": "blacklight-focus-fixed-contact-pool-v2",
        "damage_model": "literal_marvel_pool_v2",
        "stage": args.stage, "n_per_cell": n,
        "seed_formula": "first 8 bytes SHA-256 of blacklight-focus-pool-v2|stage|scenario|variant|strategy|index",
        "damage_seed_formula": "duel seed XOR 0xD6162026; separate Python Random stream",
        "source_sha256": hashes(), "python": sys.version,
        "scenarios": [{"id": name,
                       "profiles": [profile_record(p) for p in profiles]}
                      for name, profiles in configured],
        "strategies": list(STRATEGIES),
        "shield_variants": {"F0": 0, "F2": 2},
        "rows": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                      encoding="utf-8")


if __name__ == "__main__":
    main()
