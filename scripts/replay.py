"""Export one complete, independently checked combat trace as JSON."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from blacklight.audit import audit_log
from blacklight.engine import Duel, Profile, blacklight_profile
from blacklight.experiment import scenarios, seed_for, source_hashes, strategies


def profile_record(profile: Profile) -> dict:
    record = asdict(profile)
    for key in ("powers", "traits", "weapons"):
        record[key] = sorted(record[key])
    return record


def replay(stage: str, scenario_id: str, strategy_id: str,
           index: int, output: Path) -> dict:
    scenario = next(s for s in scenarios() if s.id == scenario_id)
    strategy = next(s for s in strategies() if s.id == strategy_id)
    blacklight = blacklight_profile()
    opponent = scenario.opponent
    seed = seed_for(stage, scenario_id, strategy_id, index)
    result = Duel((blacklight, opponent),
                  (strategy.policy, scenario.policy),
                  seed=seed, initial_distance=scenario.distance,
                  max_rounds=30, audit=True).run()
    issues = audit_log(
        result.log,
        {blacklight.name: blacklight.max_health,
         opponent.name: opponent.max_health},
        {blacklight.name: blacklight.max_focus,
         opponent.name: opponent.max_focus},
    )
    if issues:
        raise RuntimeError(f"Trace failed audit: {issues[:5]}")
    data = {
        "schema": "blacklight-full-trace-v1",
        "stage": stage, "scenario": scenario_id,
        "strategy": strategy_id, "index": index, "seed": seed,
        "source_sha256": source_hashes(),
        "initial_distance": scenario.distance,
        "profiles": [profile_record(blacklight), profile_record(opponent)],
        "policies": [asdict(strategy.policy), asdict(scenario.policy)],
        "result": asdict(result),
        "audit_issues": issues,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                      encoding="utf-8")
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
    args = parser.parse_args()
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
