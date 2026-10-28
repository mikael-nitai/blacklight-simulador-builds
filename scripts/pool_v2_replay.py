"""Replay and independently audit one confirmatory or reserved duel."""

from argparse import ArgumentParser
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from blacklight.audit import audit_profiled_log
from blacklight.engine import Duel, blacklight_profile
from blacklight.experiment import scenarios, seed_for, source_hashes, strategies
from blacklight.results_io import require_new_output, write_new_text
from .pool_v2_confirm import FINALISTS, holdout_scenarios, profile_record


def replay(stage: str, scenario_id: str, strategy_id: str,
           index: int, output: Path) -> dict:
    require_new_output(output)
    if stage not in ("confirm_v2", "holdout_v2") or index < 0:
        raise ValueError("Invalid stage or index")
    configured = scenarios() if stage == "confirm_v2" else holdout_scenarios()
    scenario = next(s for s in configured if s.id == scenario_id)
    if strategy_id not in FINALISTS:
        raise ValueError("Strategy was not preregistered as a finalist")
    strategy = next(s for s in strategies() if s.id == strategy_id)
    victor = blacklight_profile()
    seed = seed_for(stage, scenario.id, strategy.id, index)
    result = Duel((victor, scenario.opponent),
                  (strategy.policy, scenario.policy),
                  seed=seed, initial_distance=scenario.distance,
                  max_rounds=30, audit=True).run()
    issues = audit_profiled_log(result.log, (victor, scenario.opponent))
    if issues:
        raise RuntimeError(f"Full trace failed independent audit: {issues}")
    sources = source_hashes()
    script = Path(__file__).resolve()
    sources[script.relative_to(script.parents[1]).as_posix()] = sha256(script.read_bytes()).hexdigest()
    for name in ("scripts/pool_v2_confirm.py", "POOL_V2_CONFIRM_SPEC.md"):
        path = script.parents[1] / name
        sources[name] = sha256(path.read_bytes()).hexdigest()
    payload = {
        "schema": "blacklight-finalist-full-trace-pool-v2",
        "damage_model": "literal_marvel_pool_v2",
        "table_ruleset": "literal_marvel_pool_v2",
        "stage": stage, "scenario": scenario.id,
        "strategy": strategy.id, "index": index, "seed": seed,
        "source_sha256": sources,
        "profiles": [profile_record(p) for p in (victor, scenario.opponent)],
        "policies": [asdict(strategy.policy), asdict(scenario.policy)],
        "result": asdict(result), "audit_issues": issues,
    }
    write_new_text(output, json.dumps(payload, indent=2, ensure_ascii=False))
    return payload


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("confirm_v2", "holdout_v2"),
                        required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--strategy", choices=FINALISTS, required=True)
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument('--historical-rules', action='store_true')
    args = parser.parse_args()
    if not args.historical_rules:
        parser.error('This replay uses historical Fast Strikes rules; pass --historical-rules explicitly')
    data = replay(args.stage, args.scenario, args.strategy,
                  args.index, args.output)
    result = data["result"]
    print(f"{args.scenario} {args.strategy} #{args.index}: "
          f"{result['outcome']} winner={result['winner']}, "
          f"events={len(result['log'])}, audit=OK")


if __name__ == "__main__":
    main()
