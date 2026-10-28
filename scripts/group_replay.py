"""Export one full fixed-contact group combat with independent audit."""

from argparse import ArgumentParser
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from blacklight.results_io import require_new_output, require_unchanged_sources, write_new_text
from experimental.group import GroupBattle
from experimental.group_audit import audit_group_result
from experimental.group_policies import (GROUP_ENEMY, GROUP_FAST,
                                         GROUP_HAMMER, GROUP_HAMMER_SHIELD)
from .group_experiment import (hashes, profile_record, scenarios,
                               seed_for)


POLICIES = (GROUP_HAMMER, GROUP_HAMMER_SHIELD, GROUP_FAST)


def execution_sources() -> dict[str, str]:
    sources = hashes()
    script = Path(__file__).resolve()
    sources[script.relative_to(script.parents[1]).as_posix()] = sha256(script.read_bytes()).hexdigest()
    return sources


def replay(stage: str, scenario_id: str, policy_name: str,
           index: int, output: Path) -> dict:
    require_new_output(output)
    sources = execution_sources()
    profiles = next(value for name, value in scenarios() if name == scenario_id)
    policy = next(value for value in POLICIES if value.name == policy_name)
    seed = seed_for(stage, scenario_id, policy_name, index)
    result = GroupBattle(profiles, (policy, GROUP_ENEMY, GROUP_ENEMY),
                         seed=seed, audit=True).run()
    issues = audit_group_result(result, profiles)
    if issues:
        raise RuntimeError(f"Group replay failed audit: {issues}")
    require_unchanged_sources(sources, execution_sources())
    data = {"schema": "blacklight-group-full-trace-pool-v2",
            "evidence_scope": "exploratory_uncertified",
            "damage_model": "literal_marvel_pool_v2",
            "table_ruleset": "literal_marvel_pool_v2",
            "stage": stage, "scenario": scenario_id,
            "policy": policy_name, "index": index, "seed": seed,
            "source_sha256": sources,
            "profiles": [profile_record(p) for p in profiles],
            "policies": [asdict(policy), asdict(GROUP_ENEMY),
                         asdict(GROUP_ENEMY)],
            "result": asdict(result), "audit_issues": issues}
    write_new_text(output, json.dumps(data, ensure_ascii=False, indent=2))
    return data


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("dev", "description"),
                        default="description")
    parser.add_argument("--scenario", choices=[s[0] for s in scenarios()],
                        required=True)
    parser.add_argument("--policy", choices=[p.name for p in POLICIES],
                        required=True)
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument('--historical-rules', action='store_true')
    args = parser.parse_args()
    if not args.historical_rules:
        parser.error('This replay uses historical Fast Strikes rules; pass --historical-rules explicitly')
    if args.index < 0:
        parser.error("index must be nonnegative")
    data = replay(args.stage, args.scenario, args.policy,
                  args.index, args.output)
    result = data["result"]
    print(f"{args.output}: {result['outcome']}, rounds={result['rounds']}, "
          f"events={len(result['log'])}, limited audit=OK, scope=exploratory")


if __name__ == "__main__":
    main()
