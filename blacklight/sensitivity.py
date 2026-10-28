"""Pre-registered separate rule and sheet sensitivity runs."""

from dataclasses import replace
import json
from math import sqrt
from pathlib import Path
from statistics import NormalDist

from .engine import blacklight_profile
from .experiment import ROOT, run_cell, scenarios, source_hashes, strategies
from .results_io import historical_output, write_new_text


def difference(a: dict, b: dict) -> dict:
    p, q = a["win_rate"], b["win_rate"]
    n, m = a["n"], b["n"]
    delta = q - p
    z = NormalDist().inv_cdf(0.975)
    se = sqrt(p * (1 - p) / n + q * (1 - q) / m)
    return {"base_win_rate": p, "variant_win_rate": q,
            "difference_variant_minus_base": delta,
            "ci95_independent": [delta - z * se, delta + z * se]}


def main() -> None:
    output = historical_output(__doc__)
    scenario_map = {x.id: x for x in scenarios()}
    strategy_map = {x.id: x for x in strategies()}
    pairs = []
    for scenario_id in ("mirror_attack", "mirror_hammer", "gunner_kiter"):
        scenario = scenario_map[scenario_id]
        strategy = strategy_map["hammer"]
        canonical = run_cell("sens_sheet_canonical", scenario, strategy, 3000)
        literal = run_cell(
            "sens_sheet_literal", scenario, strategy, 3000,
            profile_override=replace(blacklight_profile(),
                                     initiative_modifier=1, run_speed=6,
                                     run_speed_exception=True))
        pairs.append({"question": "sheet_derived_vs_literal",
                      "scenario": scenario_id, "strategy": strategy.id,
                      "base": canonical, "variant": literal,
                      "comparison": difference(canonical, literal)})
        print("sheet", scenario_id, canonical["win_rate"], literal["win_rate"], flush=True)
    for scenario_id in ("mirror_attack", "mirror_hammer"):
        scenario = scenario_map[scenario_id]
        for strategy_id in ("blade_hammer_fast", "shield_blade_reactive"):
            strategy = strategy_map[strategy_id]
            healing_first = run_cell(
                "sens_heal_first", scenario, strategy, 3000,
                engine_kwargs={"end_turn_healing_first": True})
            bleed_first = run_cell(
                "sens_bleed_first", scenario, strategy, 3000,
                engine_kwargs={"end_turn_healing_first": False})
            pairs.append({"question": "end_turn_healing_vs_bleeding_order",
                          "scenario": scenario_id, "strategy": strategy_id,
                          "base": healing_first, "variant": bleed_first,
                          "comparison": difference(healing_first, bleed_first)})
            print("end_turn", scenario_id, strategy_id,
                  healing_first["win_rate"], bleed_first["win_rate"], flush=True)
            one_edge = run_cell("sens_one_edge", scenario, strategy, 3000,
                                stack_signature_edge=False)
            two_edges = run_cell("sens_two_edges", scenario, strategy, 3000,
                                 stack_signature_edge=True)
            pairs.append({"question": "signature_edge_stacking",
                          "scenario": scenario_id, "strategy": strategy_id,
                          "base": one_edge, "variant": two_edges,
                          "comparison": difference(one_edge, two_edges)})
            print("edges", scenario_id, strategy_id,
                  one_edge["win_rate"], two_edges["win_rate"], flush=True)
    payload = {"schema": "blacklight-sensitivity-v1", "n_per_cell": 3000,
               "damage_model": "literal_marvel_pool_v2",
               "table_ruleset": "literal_marvel_pool_v2",
               "seed_formula": "first 8 bytes SHA-256 of blacklight-pool-v2|stage|scenario|strategy|index",
               "source_sha256": source_hashes(), "pairs": pairs,
               "note": "Independent seeds; intervals are exploratory, not paired"}
    write_new_text(output, json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
