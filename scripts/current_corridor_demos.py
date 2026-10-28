"""Current-table corridor controls from versioned sheets; no policy ranking."""

from argparse import ArgumentParser
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from blacklight.policies import KITER
from blacklight.results_io import require_unchanged_sources, write_new_text
from combatants.battlefields import CorridorMap
from combatants.runner import run_batch, run_duel
from combatants.sheets import parse_sheet
from combatants.split_fast import SplitFastPolicy
from combatants.terrain_policies import WallAwarePolicy


ROOT = Path(__file__).resolve().parents[1]
HERO = ROOT / 'characters/victor_halle/rank3_2026-10-27_split_fast.json'
FOE = ROOT / 'characters/examples/synthetic_rank4_nonammo_gunner.json'


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--output-prefix', default='current_corridor_v1')
    args = parser.parse_args()
    if (not args.output_prefix or
            any(char not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-'
                for char in args.output_prefix)):
        parser.error('Choose a filename prefix with letters, digits, underscore or hyphen')
    names = ('blade_effects_demo', 'hammer_effects_demo', 'integration_batch')
    outputs = {name: ROOT / 'results' / f'{args.output_prefix}_{name}.json' for name in names}
    if any(path.exists() for path in outputs.values()):
        parser.error('Output already exists; choose a new versioned prefix')
    paths = (HERO, FOE, Path(__file__).resolve())
    content = {path: path.read_bytes() for path in paths}
    sources = {path.relative_to(ROOT).as_posix(): sha256(data).hexdigest()
               for path, data in content.items()}
    hero, foe = (parse_sheet(json.loads(content[path].decode('utf-8'))) for path in (HERO, FOE))
    opponent = WallAwarePolicy(**{**asdict(KITER), 'name': 'wall_aware_ranged_control'}, effect_limb=0)
    policies = {name: SplitFastPolicy(f'corridor_{name}_effects', weapon='blade', offhand='hammer',
                                      prefer_fast=True, effect_limb=limb, shield_react=True)
                for name, limb in (('blade', 0), ('hammer', 1))}
    layout = CorridorMap(12)
    payloads = {f'{name}_effects_demo': run_duel(hero, foe, policy, opponent, seed=11,
                                                battlefield=layout)
                for name, policy in policies.items()}
    for name, payload in payloads.items():
        if not any(row['type'] == 'fast_use_start' for row in payload['result']['log']):
            raise AssertionError(f'{name}: selected corridor control did not exercise Fast')
    payloads['integration_batch'] = run_batch(
        hero, foe, policies['hammer'], opponent, n=1000, master_seed=827,
        battlefield=layout, audit_every=1)
    require_unchanged_sources(sources, {path.relative_to(ROOT).as_posix(): sha256(path.read_bytes()).hexdigest()
                                        for path in paths})
    for name, payload in payloads.items():
        payload['demonstration_note'] = 'Current corridor integration control; no strategy ranking inferred'
        payload['source_sha256'].update(sources)
        write_new_text(outputs[name], json.dumps(payload, ensure_ascii=False, indent=2), newline='\n')
        if 'result' in payload:
            print(f'{name}: combat+geometry audit=OK, final positions={payload["battlefield_result"]["final_positions"]}')
        else:
            print(f'{name}: {payload["n"]} starts; {len(payload["audited_traces"])} combat+geometry traces audited')


if __name__ == '__main__':
    main()
