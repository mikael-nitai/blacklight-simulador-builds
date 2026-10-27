"""Export one full corridor combat and audit damage plus positions."""

from argparse import ArgumentParser
from dataclasses import asdict
import json
from pathlib import Path

from blacklight.audit import audit_log
from blacklight.engine import blacklight_profile
from blacklight.policies import KITER
from experimental.corridor import CorridorDuel
from experimental.corridor_audit import audit_corridor
from .corridor_experiment import (POLICIES, gunners, hashes, profile_record,
                                  seed_for)


def replay(stage: str, length: int, opponent_id: str, policy_name: str,
           index: int, output: Path) -> dict:
    opponent = next(p for name, p in gunners() if name == opponent_id)
    policy = next(p for p in POLICIES if p.name == policy_name)
    profiles = (blacklight_profile(), opponent)
    seed = seed_for(stage, length, opponent_id, policy_name, index)
    duel = CorridorDuel(profiles, (policy, KITER), seed=seed,
                        length=length, initial_positions=(0, 8), audit=True)
    result = duel.run()
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
        raise RuntimeError(f"Corridor replay failed audit: {issues}")
    victor_outcome = (result.outcome if result.outcome in
                      {"inconclusive", "draw"} else
                      "win" if result.winner == profiles[0].name else "loss")
    data = {"schema": "blacklight-corridor-full-trace-pool-v2",
            "damage_model": "literal_marvel_pool_v2",
            "stage": stage, "length": length,
            "opponent": opponent_id, "policy": policy_name,
            "index": index, "seed": seed,
            "source_sha256": hashes(),
            "profiles": [profile_record(p) for p in profiles],
            "policies": [asdict(policy), asdict(KITER)],
            "initial_positions": [0, 8],
            "final_positions": list(duel.positions),
            "wall_reached": duel.wall_reached,
            "contact_occurred": duel.contact_occurred,
            "victor_outcome": victor_outcome,
            "result": asdict(result), "audit_issues": issues}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                      encoding="utf-8")
    return data


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("dev", "description"),
                        default="description")
    parser.add_argument("--length", type=int, choices=(12, 20), required=True)
    parser.add_argument("--opponent", choices=[x[0] for x in gunners()],
                        required=True)
    parser.add_argument("--policy", choices=[p.name for p in POLICIES],
                        required=True)
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.index < 0:
        parser.error("index must be nonnegative")
    data = replay(args.stage, args.length, args.opponent,
                  args.policy, args.index, args.output)
    result = data["result"]
    print(f"{args.output}: Victor {data['victor_outcome']}, rounds={result['rounds']}, "
          f"positions={data['final_positions']}, events={len(result['log'])}, audit=OK")


if __name__ == "__main__":
    main()
