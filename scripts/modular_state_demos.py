"""Export full character-sheet replays for migrated standard state actions.

These are refactor demonstrations with explicit control policies, not a new
strategy-performance experiment.
"""

from hashlib import sha256
import json
from pathlib import Path
from blacklight.results_io import write_new_text
from argparse import ArgumentParser

from blacklight.policies import ATTACK, RulePolicy, STANCE
from combatants import load_sheet
from combatants.runner import run_duel


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--output-prefix', default='generic_sheet_lifecycle_v3')
    args = parser.parse_args()
    if not args.output_prefix or any(char not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for char in args.output_prefix):
        parser.error('Output prefix must contain only letters, digits, underscore or hyphen')
    hero = load_sheet(ROOT / 'characters/victor_halle/rank3_2026-10-26.json')
    opponent = load_sheet(ROOT / 'characters/examples/synthetic_rank4.json')
    cases = (
        ('stance', STANCE, 7, 'stance'),
        ('standard_shield', RulePolicy('standard_shield_control', weapon='hammer',
                                      shield_standard=True), 8, 'shield_activate'),
        ('dodge', RulePolicy('dodge_control', dodge_below_health=150), 9, 'dodge'),
    )
    script = Path(__file__).resolve()
    for name, policy, seed, event_type in cases:
        result = run_duel(hero, opponent, policy, ATTACK, seed=seed, max_rounds=10)
        count = sum(event['type'] == event_type for event in result['result']['log'])
        if count < 1:
            raise RuntimeError(f'{name}: selected demonstration did not exercise the action')
        result['source_sha256']['scripts/modular_state_demos.py'] = sha256(script.read_bytes()).hexdigest()
        result['demonstration_note'] = 'Refactor control policy; no strategy recommendation inferred'
        output = ROOT / 'results' / f'{args.output_prefix}_{name}_demo.json'
        content = json.dumps(result, ensure_ascii=False, indent=2)
        if output.exists() and output.read_bytes() != content.encode('utf-8'):
            raise ValueError(f'{output.name}: existing result differs; use a new output prefix')
        if not output.exists():
            write_new_text(output, content, newline='\n')
        print(f'{name}: {result["hero_outcome"]}, {count} activation events, audit=OK')


if __name__ == '__main__':
    main()
