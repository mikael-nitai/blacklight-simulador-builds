"""Export full character-sheet replays for migrated standard state actions.

These are refactor demonstrations with explicit control policies, not a new
strategy-performance experiment.
"""

from hashlib import sha256
import json
from pathlib import Path

from blacklight.policies import ATTACK, RulePolicy, STANCE
from combatants import load_sheet
from combatants.runner import run_duel


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
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
        output = ROOT / 'results' / f'generic_sheet_{name}_demo.json'
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2),
                          encoding='utf-8', newline='\n')
        print(f'{name}: {result["hero_outcome"]}, {count} activation events, audit=OK')


if __name__ == '__main__':
    main()
