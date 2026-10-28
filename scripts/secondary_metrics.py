"""Supplemental distributions, survival horizons, and own-turn damage."""

from hashlib import sha256
import json
from math import sqrt
from pathlib import Path
import sys

from blacklight.audit import audit_profiled_log
from blacklight.engine import Duel, blacklight_profile
from blacklight.experiment import ROOT, scenarios, seed_for, source_hashes, strategies, wilson
from blacklight.results_io import historical_output, require_unchanged_sources, write_new_text


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    at = (len(ordered) - 1) * probability
    lo = int(at)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (at - lo)


def mean_se(values: list[float]) -> dict[str, float]:
    n = len(values)
    avg = sum(values) / n
    variance = sum((x - avg) ** 2 for x in values) / (n - 1)
    return {"mean": avg, "mc_se": sqrt(variance / n)}


def execution_sources() -> dict[str, str]:
    sources = source_hashes()
    for name in ('scripts/secondary_metrics.py', 'SECONDARY_SPEC.md'):
        sources[name] = sha256((ROOT / name).read_bytes()).hexdigest()
    return sources


def main() -> None:
    output = historical_output(__doc__)
    sources = execution_sources()
    chosen = {"bare_attack", "hammer", "shield_hammer_reactive",
              "hammer_heal_t75_s15", "shield_hammer_endturn"}
    selected = tuple(s for s in strategies() if s.id in chosen)
    n = 1000
    rows = []
    for scenario in scenarios():
        for strategy in selected:
            damages: list[float] = []
            per_turn: list[float] = []
            own_turns: list[float] = []
            final_health: list[float] = []
            survived = {3: 0, 5: 0, 10: 0}
            outcomes = {"win": 0, "loss": 0, "inconclusive": 0, "draw": 0}
            for index in range(n):
                profile = blacklight_profile()
                seed = seed_for("secondary", scenario.id, strategy.id, index)
                result = Duel((profile, scenario.opponent),
                              (strategy.policy, scenario.policy), seed=seed,
                              initial_distance=scenario.distance, max_rounds=30,
                              audit=True).run()
                issues = audit_profiled_log(result.log, (profile, scenario.opponent))
                if issues:
                    raise RuntimeError(f"{scenario.id}/{strategy.id}/{index}: {issues[:3]}")
                blacklight_won = result.winner == profile.name
                outcome = ("inconclusive" if result.outcome == "inconclusive"
                           else "draw" if result.outcome == "draw"
                           else "win" if blacklight_won else "loss")
                outcomes[outcome] += 1
                for horizon in survived:
                    if blacklight_won or result.rounds > horizon or outcome == "inconclusive":
                        survived[horizon] += 1
                turns = sum(e["type"] == "turn_start" and e["actor"] == profile.name
                            for e in result.log)
                damage = result.metrics[0]["damage_dealt"]
                damages.append(float(damage))
                own_turns.append(float(turns))
                per_turn.append(damage / turns if turns else 0.0)
                final_health.append(float(result.final_health[0]))
            rows.append({
                "scenario": scenario.id, "strategy": strategy.id, "n": n,
                "outcomes": outcomes,
                "survival_through_round": {
                    str(h): {"count": count, "rate": count / n,
                             "ci95_wilson": wilson(count, n)}
                    for h, count in survived.items()},
                "damage_total": {"mean_se": mean_se(damages),
                                 "p10": quantile(damages, .1),
                                 "median": quantile(damages, .5),
                                 "p90": quantile(damages, .9)},
                "damage_per_own_turn": {"mean_se": mean_se(per_turn),
                                        "median": quantile(per_turn, .5)},
                "own_turns": mean_se(own_turns),
                "final_health": {"mean_se": mean_se(final_health),
                                 "median": quantile(final_health, .5)},
                "audited_full_logs": n,
            })
            print(f"secondary {scenario.id} {strategy.id}: {n} audited", flush=True)
    require_unchanged_sources(sources, execution_sources())
    payload = {
        "schema": "blacklight-secondary-v1", "n_per_cell": n,
        "damage_model": "literal_marvel_pool_v2",
        "table_ruleset": "literal_marvel_pool_v2",
        "seed_formula": "first 8 bytes SHA-256 of blacklight-pool-v2|secondary|scenario|strategy|index",
        "source_sha256": sources,
        "script_sha256": sources['scripts/secondary_metrics.py'],
        "spec_sha256": sources['SECONDARY_SPEC.md'],
        "python": sys.version, "rows": rows,
    }
    write_new_text(output, json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
