"""Reproducible exploratory and confirmatory restricted-duel experiments."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from hashlib import sha256
import json
from math import isclose, isfinite, sqrt
from pathlib import Path
from statistics import NormalDist
import sys

from . import __version__
from .engine import Duel, Profile, blacklight_profile
from .results_io import require_new_output, write_new_text
from .policies import (ATTACK, BLADE_HAMMER_FAST, CLAW_HAMMER_FAST,
                       HAMMER, HAMMER_FAST, HYBRID,
                       KITER, RulePolicy, SHIELD_BLADE_REACTIVE,
                       SHIELD_HAMMER_ENDTURN, SHIELD_HAMMER_REACTIVE,
                       SHIELD_BLADE_HAMMER_REACTIVE, STANCE)


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Strategy:
    id: str
    policy: RulePolicy


@dataclass(frozen=True)
class Scenario:
    id: str
    opponent: Profile
    policy: RulePolicy
    distance: int


def strategies() -> tuple[Strategy, ...]:
    return (
        Strategy("bare_attack", ATTACK),
        Strategy("stance_bare", STANCE),
        Strategy("hammer", HAMMER),
        Strategy("blade_hammer_fast", BLADE_HAMMER_FAST),
        Strategy("hammer_fast", HAMMER_FAST),
        Strategy("claw_hammer_fast", CLAW_HAMMER_FAST),
        Strategy("shield_blade_hammer_reactive", SHIELD_BLADE_HAMMER_REACTIVE),
        Strategy("hammer_heal", replace(HAMMER, name="hammer_heal", heal_missing=30)),
        Strategy("shield_blade_reactive", SHIELD_BLADE_REACTIVE),
        Strategy("shield_hammer_reactive", SHIELD_HAMMER_REACTIVE),
        Strategy("hybrid", replace(HYBRID, name="hybrid", weapon="hammer")),
        Strategy("hammer_heal_t75_s15", replace(
            HAMMER, name="hammer_heal_t75_s15", heal_missing=75,
            heal_spend=15)),
        Strategy("shield_hammer_endturn", SHIELD_HAMMER_ENDTURN),
    )


def scenarios() -> tuple[Scenario, ...]:
    mirror = replace(blacklight_profile(), name="Enemy")
    gunner = Profile(
        "Gunner", rank=3, max_health=120, max_focus=60,
        melee=2, agility=6, resilience=4, vigilance=2,
        logic=2,
        melee_defense=12, agility_defense=16, run_speed=6,
        ranged_range=10, ranged_is_ammunition=True,
    )
    return (
        Scenario("mirror_attack", mirror, ATTACK, 1),
        Scenario("mirror_hammer", mirror, HAMMER, 1),
        Scenario("mirror_shield", mirror, SHIELD_HAMMER_REACTIVE, 1),
        Scenario("gunner_kiter", gunner, KITER, 8),
    )


def seed_for(stage: str, scenario: str, strategy: str, index: int) -> int:
    key = f"blacklight-pool-v2|{stage}|{scenario}|{strategy}|{index}".encode("utf-8")
    return int.from_bytes(sha256(key).digest()[:8], "big")


def source_hashes() -> dict[str, str]:
    paths = list((ROOT / "blacklight").glob("*.py")) + [
        ROOT / "EXPERIMENT_SPEC.md", ROOT / "RULES_AUDIT.md",
        ROOT / "CHARACTER_AUDIT.md",
        ROOT / "DAMAGE_POOL_V2_SPEC.md", ROOT / "DAMAGE_POOL_RULING.md",
        ROOT / "FAST_STRIKES_RULING.md",
    ]
    return {path.relative_to(ROOT).as_posix(): sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths)}


@dataclass
class Moment:
    n: int = 0
    total: float = 0.0
    square_total: float = 0.0

    def add(self, value: float) -> None:
        self.n += 1
        self.total += value
        self.square_total += value * value

    def summary(self) -> dict[str, float | None]:
        if self.n < 1:
            raise ValueError('A mean requires at least one observation')
        mean = self.total / self.n
        if self.n == 1:
            return {"mean": mean, "mc_se": None}
        variance = max(0.0, (self.square_total - self.n * mean * mean) / (self.n - 1))
        return {"mean": mean, "mc_se": sqrt(variance / self.n)}


def wilson(successes: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    if (type(successes) is not int or type(n) is not int or n < 1
            or not 0 <= successes <= n or type(alpha) not in (int, float)
            or not isfinite(alpha) or not 0 < alpha < 1):
        raise ValueError('Wilson interval requires valid binomial counts and 0 < alpha < 1')
    z = NormalDist().inv_cdf(1 - alpha / 2)
    p = successes / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, center - half), min(1.0, center + half)


def win_counts(row: dict) -> tuple[int, int]:
    """Recover binomial counts and reject a rate inconsistent with the sample."""
    n, rate = row['n'], row['win_rate']
    if (type(n) is not int or n < 1 or type(rate) not in (int, float)
            or not isfinite(rate) or not 0 <= rate <= 1):
        raise ValueError('Win rate requires a positive integer sample and a finite proportion')
    wins = round(rate * n)
    if not isclose(rate, wins / n, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError('Win rate does not correspond to an integer count')
    if 'outcomes' in row:
        outcomes = row['outcomes']
        if (not isinstance(outcomes, dict) or type(outcomes.get('win')) is not int
                or outcomes['win'] != wins):
            raise ValueError('Win rate disagrees with the recorded outcome count')
    return wins, n


def independent_win_difference(first: dict, second: dict, *, alpha: float = 0.05) -> tuple[float, float, float]:
    """Newcombe/Wilson interval for first minus second, with independent samples."""
    wins_a, n_a = win_counts(first)
    wins_b, n_b = win_counts(second)
    p, q = wins_a / n_a, wins_b / n_b
    low_a, high_a = wilson(wins_a, n_a, alpha=alpha)
    low_b, high_b = wilson(wins_b, n_b, alpha=alpha)
    delta = p - q
    lower = delta - sqrt((p - low_a) ** 2 + (high_b - q) ** 2)
    upper = delta + sqrt((high_a - p) ** 2 + (q - low_b) ** 2)
    return delta, max(-1.0, lower), min(1.0, upper)


def run_cell(stage: str, scenario: Scenario, strategy: Strategy, n: int,
             *, stack_signature_edge: bool = True,
             profile_override: Profile | None = None,
             engine_kwargs: dict | None = None) -> dict:
    outcomes = {"win": 0, "loss": 0, "inconclusive": 0, "draw": 0}
    keys = ("rounds", "turns", "final_health", "final_focus", "damage_dealt",
            "damage_taken", "damage_mitigated", "healing_effective",
            "focus_spent", "damage_round3", "damage_round5", "damage_round10")
    moments = {key: Moment() for key in keys}
    totals = {key: 0 for key in ("attacks", "hits", "fantastic_hits", "ripostes",
                                "stuns_applied", "blade_bonus_actions")}
    profile = profile_override or blacklight_profile()
    for index in range(n):
        seed = seed_for(stage, scenario.id, strategy.id, index)
        result = Duel((profile, scenario.opponent), (strategy.policy, scenario.policy),
                      seed=seed, initial_distance=scenario.distance,
                      max_rounds=30, stack_signature_edge=stack_signature_edge,
                      **(engine_kwargs or {})).run()
        if result.outcome == "inconclusive":
            outcomes["inconclusive"] += 1
        elif result.outcome == "draw":
            outcomes["draw"] += 1
        elif result.winner == "Blacklight":
            outcomes["win"] += 1
        else:
            outcomes["loss"] += 1
        m = result.metrics[0]
        for key, value in (("rounds", result.rounds), ("turns", result.turns),
                           ("final_health", result.final_health[0]),
                           ("final_focus", result.final_focus[0])):
            moments[key].add(value)
        for key in keys[4:]:
            moments[key].add(m[key])
        for key in totals:
            totals[key] += m[key]
    if sum(outcomes.values()) != n:
        raise RuntimeError("Outcome count mismatch")
    return {
        "stage": stage, "scenario": scenario.id, "strategy": strategy.id,
        "n": n, "stack_signature_edge": stack_signature_edge,
        "profile_override": None if profile_override is None else
            {"initiative_modifier": profile.initiative_modifier,
             "run_speed": profile.run_speed,
             "run_speed_exception": profile.run_speed_exception},
        "engine_kwargs": engine_kwargs or {},
        "outcomes": outcomes,
        "win_rate": outcomes["win"] / n,
        "win_ci95_wilson": wilson(outcomes["win"], n),
        "metrics_all_starts": {key: moment.summary() for key, moment in moments.items()},
        "event_totals": totals,
    }


def comparisons(rows: list[dict]) -> list[dict]:
    by_scenario = {scenario.id: {r["strategy"]: r for r in rows
                                 if r["scenario"] == scenario.id}
                   for scenario in scenarios()}
    result = []
    m = len(strategies()) - 1
    for scenario, block in by_scenario.items():
        base = block["bare_attack"]
        for strategy, row in block.items():
            if strategy == "bare_attack":
                continue
            delta, lower, upper = independent_win_difference(row, base, alpha=0.05 / m)
            result.append({"scenario": scenario, "strategy": strategy,
                           "vs": "bare_attack", "win_difference": delta,
                           "simultaneous_ci_bonferroni": [lower, upper],
                           "method": "Newcombe/Wilson, independent Bernoulli samples; "
                                     "approximate Bonferroni adjustment within scenario"})
    return result


def execute(stage: str, n: int, output: Path,
            *, stack_signature_edge: bool = True) -> dict:
    require_new_output(output)
    if n < 1:
        raise ValueError("n must be positive")
    rows = []
    for scenario in scenarios():
        for strategy in strategies():
            row = run_cell(stage, scenario, strategy, n,
                           stack_signature_edge=stack_signature_edge)
            rows.append(row)
            print(f"{stage} {scenario.id} {strategy.id}: "
                  f"{row['outcomes']['win']}/{n} wins", flush=True)
    payload = {
        "schema": "blacklight-restricted-duel-pool-v2", "engine_version": __version__,
        "damage_model": "literal_marvel_pool_v2",
        "table_ruleset": "literal_marvel_pool_v2",
        "stage": stage, "n_per_cell": n,
        "seed_formula": "first 8 bytes SHA-256 of blacklight-pool-v2|stage|scenario|strategy|index",
        "damage_seed_formula": "duel seed XOR 0xD6162026; separate Python Random stream",
        "python": sys.version, "source_sha256": source_hashes(),
        "rows": rows, "comparisons": comparisons(rows),
        "limitations": ["two-combatant open field", "no numeric limb effect",
                        "no Focus damage/Karma", "no multi-target Fast Strikes",
                        "shield starts inactive; activation costs standard action or reaction"],
    }
    write_new_text(output, json.dumps(payload, indent=2, ensure_ascii=False))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("smoke", "dev", "confirm"), required=True)
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument('--historical-rules', action='store_true')
    parser.add_argument("--one-edge-counterfactual", action="store_true",
                        help="Sensitivity run only; disables the confirmed second Fast Strikes edge")
    args = parser.parse_args()
    if not args.historical_rules:
        parser.error('This experiment uses the historical single-check Fast rules; pass --historical-rules explicitly')
    if args.output.exists():
        parser.error('Output already exists; choose a new versioned filename')
    execute(args.stage, args.n, args.output,
            stack_signature_edge=not args.one_edge_counterfactual)


if __name__ == "__main__":
    main()
