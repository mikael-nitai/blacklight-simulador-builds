"""Export one audited full Mental Punch duel trace."""

from argparse import ArgumentParser
from dataclasses import asdict
import json
from pathlib import Path

from blacklight.engine import blacklight_profile
from blacklight.results_io import require_new_output, write_new_text
from experimental.focus_audit import audit_focus_duel
from experimental.focus_duel import FocusDuel, STRATEGIES
from .focus_experiment import hashes, mentalist, profile_record, seed_for


def replay(stage: str, scenario: str, variant: str,
           strategy: str, index: int, output: Path) -> dict:
    require_new_output(output)
    rank = int(scenario[1:])
    profiles = (blacklight_profile(), mentalist(rank))
    reduction = 0 if variant == "F0" else 2
    seed = seed_for(stage, scenario, variant, strategy, index)
    result = FocusDuel(*profiles, strategy=strategy,
                       shield_focus_reduction=reduction,
                       seed=seed, audit=True).run()
    issues = audit_focus_duel(result, profiles, reduction)
    if issues:
        raise RuntimeError(f"Focus replay failed audit: {issues}")
    data = {"schema": "blacklight-focus-full-trace-pool-v2",
            "damage_model": "literal_marvel_pool_v2",
            "stage": stage, "scenario": scenario,
            "variant": variant, "strategy": strategy,
            "index": index, "seed": seed,
            "source_sha256": hashes(),
            "profiles": [profile_record(p) for p in profiles],
            "result": asdict(result), "audit_issues": issues}
    write_new_text(output, json.dumps(data, indent=2, ensure_ascii=False))
    return data


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("dev", "description"),
                        default="description")
    parser.add_argument("--scenario", choices=("M3", "M4"), required=True)
    parser.add_argument("--variant", choices=("F0", "F2"), required=True)
    parser.add_argument("--strategy", choices=STRATEGIES, required=True)
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.index < 0:
        parser.error("index must be nonnegative")
    data = replay(args.stage, args.scenario, args.variant,
                  args.strategy, args.index, args.output)
    result = data["result"]
    print(f"{args.output}: {result['outcome']}, rounds={result['rounds']}, "
          f"focus={result['final_focus'][0]}, events={len(result['log'])}, audit=OK")


if __name__ == "__main__":
    main()
