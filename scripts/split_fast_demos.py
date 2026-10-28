"""Export current-rule character demonstrations and a sheet-swap integration batch.

These are execution controls; no policy is selected as optimal from this sample.
"""

from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path

from blacklight.policies import ATTACK
from blacklight.results_io import require_unchanged_sources, write_new_text
from combatants.runner import run_batch, run_duel
from combatants.sheets import parse_sheet
from combatants.split_fast import SplitFastPolicy


ROOT = Path(__file__).resolve().parents[1]
HERO = ROOT / 'characters/victor_halle/rank3_2026-10-27_split_fast.json'
FOE = ROOT / 'characters/examples/synthetic_rank4_split_fast.json'


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--output-prefix', default='split_fast_v3')
    args = parser.parse_args()
    if (not args.output_prefix or
            any(char not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-'
                for char in args.output_prefix)):
        parser.error('Choose a filename prefix containing only letters, digits, underscore or hyphen')
    names = ('blade_effects_demo', 'hammer_effects_demo', 'rank4_integration_batch')
    outputs = {name: ROOT / 'results' / f'{args.output_prefix}_{name}.json' for name in names}
    if any(path.exists() for path in outputs.values()):
        parser.error('Output already exists; choose a new versioned prefix')
    paths = (HERO, FOE, Path(__file__).resolve())
    content = {path: path.read_bytes() for path in paths}
    sources = {path.relative_to(ROOT).as_posix(): sha256(data).hexdigest()
               for path, data in content.items()}
    hero, foe = (parse_sheet(json.loads(content[path].decode('utf-8'))) for path in (HERO, FOE))
    policies = {name: SplitFastPolicy(f'current_{name}', weapon='blade', offhand='hammer',
                                      prefer_fast=True, effect_limb=selected, shield_react=True)
                for name, selected in (('blade', 0), ('hammer', 1))}
    payloads = {f'{name}_effects_demo': run_duel(hero, foe, policy, ATTACK, seed=51)
                for name, policy in policies.items()}
    for name, payload in payloads.items():
        if not any(row['type'] == 'fast_use_start' for row in payload['result']['log']):
            raise AssertionError(f'{name}: selected demonstration did not exercise Fast')
    payloads['rank4_integration_batch'] = run_batch(
        foe, hero, ATTACK, policies['hammer'], n=1000, master_seed=731, audit_every=1)
    require_unchanged_sources(sources, {path.relative_to(ROOT).as_posix(): sha256(path.read_bytes()).hexdigest()
                                        for path in paths})
    for name, payload in payloads.items():
        payload['demonstration_note'] = 'Current table execution/integration control; no strategy ranking inferred'
        payload['source_sha256'].update(sources)
        write_new_text(outputs[name], json.dumps(payload, ensure_ascii=False, indent=2), newline='\n')
        if 'result' in payload:
            checks = sum(row['type'] == 'fast_limb_check' for row in payload['result']['log'])
            print(f'{name}: audit=OK, {checks} separate limb checks')
        else:
            print(f'{name}: {payload["n"]} duels, {len(payload["audited_traces"])} full traces audited')


if __name__ == '__main__':
    main()
