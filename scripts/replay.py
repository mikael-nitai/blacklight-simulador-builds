"""Export one complete, independently checked combat trace as JSON."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from blacklight.audit import audit_profiled_log
from blacklight.engine import Duel, Profile, blacklight_profile
from blacklight.experiment import ROOT, scenarios, seed_for, source_hashes, strategies
from blacklight.results_io import require_new_output, require_unchanged_sources, write_new_text
from blacklight.result_audit import audit_battle_result
from blacklight.rulesets import LEGACY_RULESET
from blacklight.spatial_audit import audit_open_field_distance


def execution_sources() -> dict[str, str]:
    sources = source_hashes()
    script = Path(__file__).resolve()
    sources[script.relative_to(ROOT).as_posix()] = sha256(script.read_bytes()).hexdigest()
    return sources


def profile_record(profile: Profile) -> dict:
    record = asdict(profile)
    for key in ("powers", "traits", "weapons"):
        record[key] = sorted(record[key])
    return record


def replay(stage: str, scenario_id: str, strategy_id: str,
           index: int, output: Path) -> dict:
    require_new_output(output)
    sources = execution_sources()
    scenario = next(s for s in scenarios() if s.id == scenario_id)
    strategy = next(s for s in strategies() if s.id == strategy_id)
    blacklight = blacklight_profile()
    opponent = scenario.opponent
    seed = seed_for(stage, scenario_id, strategy_id, index)
    result = Duel((blacklight, opponent),
                  (strategy.policy, scenario.policy),
                  seed=seed, initial_distance=scenario.distance,
                  max_rounds=30, audit=True).run()
    issues = audit_profiled_log(result.log, (blacklight, opponent), ruleset=LEGACY_RULESET)
    issues.extend(audit_battle_result(result, (blacklight, opponent), expected_seed=seed, max_rounds=30))
    issues.extend(audit_open_field_distance(result.log, scenario.distance))
    if issues:
        raise RuntimeError(f"Trace failed audit: {issues[:5]}")
    require_unchanged_sources(sources, execution_sources())
    data = {
        "schema": "blacklight-full-trace-pool-v2",
        "damage_model": "literal_marvel_pool_v2",
        "table_ruleset": "literal_marvel_pool_v2",
        "damage_seed_formula": "duel seed XOR 0xD6162026; separate Python Random stream",
        "stage": stage, "scenario": scenario_id,
        "strategy": strategy_id, "index": index, "seed": seed,
        "source_sha256": sources,
        "initial_distance": scenario.distance,
        "profiles": [profile_record(blacklight), profile_record(opponent)],
        "policies": [asdict(strategy.policy), asdict(scenario.policy)],
        "result": asdict(result),
        "audit_issues": issues,
    }
    write_new_text(output, json.dumps(data, ensure_ascii=False, indent=2))
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", default="demo")
    parser.add_argument("--scenario", required=True,
                        choices=[s.id for s in scenarios()])
    parser.add_argument("--strategy", required=True,
                        choices=[s.id for s in strategies()])
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument('--historical-rules', action='store_true')
    args = parser.parse_args()
    if not args.historical_rules:
        parser.error('This replay uses historical Fast Strikes rules; pass --historical-rules explicitly')
    if args.index < 0:
        parser.error("index must be nonnegative")
    data = replay(args.stage, args.scenario, args.strategy,
                  args.index, args.output)
    result = data["result"]
    print(f"{args.output}: {result['outcome']}, winner={result['winner']}, "
          f"rounds={result['rounds']}, events={len(result['log'])}, "
          f"audit=OK")


if __name__ == "__main__":
    main()
