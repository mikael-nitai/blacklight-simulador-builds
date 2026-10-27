"""Read-only audit of zero-cost state action migration.

Run from repository root: python -B -m scripts.audit_modular_states
Only compares mechanics and reports a malformed-definition finding; no files
are written and no strategy performance is estimated.
"""

from dataclasses import replace
from hashlib import sha256
from itertools import product
import json
from pathlib import Path
import sys

from blacklight.engine import Action, Duel, IllegalAction, Profile, blacklight_profile
from blacklight.policies import ATTACK, RulePolicy, STANCE
from combatants.actions import (ActionRegistry, CapabilityRequirement, CombatState,
                                FocusSelfHeal, StateActivation)
from combatants.modular_duel import ModularDuel
from combatants.runner import run_batch, run_duel
from combatants.sheets import load_sheet


ROOT = Path(__file__).resolve().parents[1]
STATE_KINDS = {'stance', 'shield', 'dodge'}


def profile(*, power: bool, weapon: bool, trait: bool = False) -> Profile:
    return Profile('A', 3, 100, 90, 1, 1, 1, 1, 11, 11, 5,
                   powers=frozenset({'attack_stance'} if power else ()),
                   traits=frozenset({'combat_reflexes'} if trait else ()),
                   weapons=frozenset({'shield'} if weapon else ()))


def setup(cls, hero: Profile, *, registry=None):
    foe = Profile('B', 3, 100, 90, 1, 1, 1, 1, 11, 11, 5)
    kwargs = {'seed': 8, 'audit': True}
    if registry is not None:
        kwargs['action_registry'] = registry
    duel = cls((hero, foe), (None, None), **kwargs)
    duel.round = 1
    duel.active_actor = 0
    duel.fighters[0].standard_available = True
    return duel


def apply_fixture(duel, *, stance, shield, dodge, focus, health, stunned,
                  standard_available):
    fighter = duel.fighters[0]
    fighter.stance = stance
    fighter.shield_active = shield
    fighter.dodging = dodge
    fighter.focus = focus
    fighter.health = health
    fighter.stunned_by = 1 if stunned else None
    fighter.standard_available = standard_available


def state_grid_oracle() -> tuple[int, int]:
    states = transitions = 0
    for power, weapon, stance, shield, dodge, focus, health, stunned, standard in product(
            (False, True), (False, True), (False, True), (False, True),
            (False, True), (-5, 0, 1, 5, 90), (0, 100), (False, True),
            (False, True)):
        hero = profile(power=power, weapon=weapon)
        old, new = setup(Duel, hero), setup(ModularDuel, hero)
        fixture = dict(stance=stance, shield=shield, dodge=dodge,
                       focus=focus, health=health, stunned=stunned,
                       standard_available=standard)
        for duel in (old, new):
            apply_fixture(duel, **fixture)
        actions = old.legal_actions(0)
        if actions != new.legal_actions(0):
            raise AssertionError(('legal_actions', fixture, power, weapon))
        states += 1
        for action in actions:
            if action.kind not in STATE_KINDS:
                continue
            old_one, new_one = setup(Duel, hero), setup(ModularDuel, hero)
            for duel in (old_one, new_one):
                apply_fixture(duel, **fixture)
                duel._act(0, action)
            if ([vars(x) for x in old_one.fighters] !=
                    [vars(x) for x in new_one.fighters] or old_one.log != new_one.log):
                raise AssertionError(('state_transition', fixture, action))
            if (new_one.fighters[0].focus != focus or
                    new_one.fighters[0].focus_spent != 0 or
                    any(row['type'] == 'focus_spent' for row in new_one.log)):
                raise AssertionError(('zero_cost_changed_focus', fixture, action))
            transitions += 1
    return states, transitions


def combined_requirement_oracle() -> int:
    requirements = (CapabilityRequirement('power', 'attack_stance'),
                    CapabilityRequirement('trait', 'combat_reflexes'),
                    CapabilityRequirement('weapon', 'shield'))
    module = StateActivation('fixture_mode', requirements, CombatState.DODGE,
                             False, ('AUDIT-ONLY',), ('Synthetic audit case',))
    registry = ActionRegistry((module,))
    cases = 0
    for power, trait, weapon in product((False, True), repeat=3):
        duel = setup(ModularDuel, profile(power=power, weapon=weapon,
                                          trait=trait), registry=registry)
        listed = Action('fixture_mode') in duel.legal_actions(0)
        if listed != (power and trait and weapon):
            raise AssertionError(('combined_requirements', power, trait, weapon))
        cases += 1
    return cases


def complete_replay_oracle() -> int:
    player = blacklight_profile()
    foe = Profile('Other', 3, 90, 60, 4, 2, 3, 2, 14, 12, 5)
    policies = (STANCE,
                RulePolicy('standard_shield', weapon='hammer', shield_standard=True),
                RulePolicy('dodge', dodge_below_health=150))
    count = 0
    for policy, distance, seed in product(policies, (1, 5, 12), range(40)):
        options = dict(seed=seed, initial_distance=distance,
                       max_rounds=15, audit=True)
        old = Duel((player, foe), (policy, ATTACK), **options).run()
        new = ModularDuel((player, foe), (policy, ATTACK), **options).run()
        if old != new:
            raise AssertionError(('complete_replay', policy.name, distance, seed))
        count += 1
    return count


def malformed_definition_probe() -> dict:
    """Require the former malformed-definition leak to fail during setup."""
    factories = (
        ('mode', lambda: StateActivation('mode', (), CombatState.DODGE, False,
                                        ['AUDIT-ONLY'], ('Synthetic audit case',)),
         Action('mode')),
        ('heal2', lambda: FocusSelfHeal('heal2', 'do_this_all_day', 5, 5, 1, 2,
                                        ['AUDIT-ONLY'], 'AUDIT-ONLY',
                                        ('Synthetic audit case',)),
         Action('heal2', 5)),
    )
    findings = {}
    for name, factory, action in factories:
        try:
            module = factory()
            registry = ActionRegistry((module,))
        except ValueError:
            findings[name] = 'rejected_at_constructor_or_registration'
            continue
        hero = replace(profile(power=False, weapon=False),
                       powers=frozenset({'do_this_all_day'}))
        duel = setup(ModularDuel, hero, registry=registry)
        listed = action in duel.legal_actions(0)
        before = (duel.fighters[0].focus, duel.fighters[0].health,
                  duel.fighters[0].standard_available, tuple(duel.log))
        rejected = False
        try:
            duel._act(0, action)
        except IllegalAction:
            rejected = True
        after = (duel.fighters[0].focus, duel.fighters[0].health,
                 duel.fighters[0].standard_available, tuple(duel.log))
        findings[name] = {'listed_as_legal': listed,
                          'rejected_on_execution': rejected,
                          'mutated': before != after}
    if any(value != 'rejected_at_constructor_or_registration'
           for value in findings.values()):
        raise AssertionError(('malformed_definition_not_rejected_early', findings))
    return findings


def malformed_request_probe() -> dict:
    """Require strict type rejection before dataclass value equality is used."""
    findings = {}
    for action in (Action('stance', 0.0), Action('shield', 0.0),
                   Action('dodge', False)):
        duel = setup(ModularDuel, blacklight_profile())
        listed = action in duel.legal_actions(0)
        fighter = duel.fighters[0]
        before = (fighter.health, fighter.focus, fighter.focus_spent,
                  fighter.standard_available, tuple(duel.log))
        rejected = False
        try:
            duel._act(0, action)
        except IllegalAction:
            rejected = True
        after = (fighter.health, fighter.focus, fighter.focus_spent,
                 fighter.standard_available, tuple(duel.log))
        if not rejected or after != before:
            raise AssertionError(('malformed_request_not_atomic_failure', action))
        findings[f'{action.kind}:{type(action.focus).__name__}'] = {
            'matches_canonical_legal_action': listed,
            'rejected_on_execution': rejected,
            'mutated': after != before,
            'focus_after': duel.fighters[0].focus,
        }
    return findings


def runner_smoke_oracle() -> int:
    hero = load_sheet(ROOT / 'characters/examples/synthetic_rank4.json')
    foe = load_sheet(ROOT / 'characters/victor_halle/rank3_2026-10-26.json')
    duel = run_duel(hero, foe, ATTACK, ATTACK, seed=402)
    batch = run_batch(hero, foe, ATTACK, ATTACK, n=2, master_seed=402,
                      audit_every=1)
    for result in (duel, batch):
        if (result.get('audit_issues') or
                result['execution_adapter'] != 'modular_physical_duel_v2' or
                {row['kind'] for row in result['registered_action_modules']} !=
                STATE_KINDS | {'heal'}):
            raise AssertionError('runner did not use audited modular default registry')
        runtime = result.get('runtime', {})
        if (runtime.get('python') != sys.version or
                runtime.get('implementation') != sys.implementation.name or
                runtime.get('combat_core_dependencies') != 'Python standard library' or
                'transitive external dependencies need a separate manifest' not in
                runtime.get('external_policy_dependency_scope', '')):
            raise AssertionError('runner runtime provenance is incomplete')
        manifest = {name.replace('\\', '/'): digest
                    for name, digest in result['source_sha256'].items()}
        for relative in ('blacklight/engine.py', 'blacklight/policies.py',
                         'combatants/actions.py', 'combatants/modular_duel.py',
                         'combatants/runner.py'):
            if manifest.get(relative) != sha256((ROOT / relative).read_bytes()).hexdigest():
                raise AssertionError(('missing_or_incorrect_source_hash', relative))
        definitions = {row['kind']: row for row in result['registered_action_modules']}
        if (definitions['heal']['health_per_focus'] != 2 or
                definitions['heal']['minimum_spend'] != 5 or
                definitions['stance']['state'] != CombatState.ATTACK_STANCE or
                definitions['shield']['rules'] != ('HR-04',) or
                definitions['dodge']['require_inactive'] is not False):
            raise AssertionError('runner metadata omitted action parameters')
    if batch['source_sha256'] != duel['source_sha256']:
        raise AssertionError('batch and duel source manifests differ')
    return 2


def main() -> None:
    states, transitions = state_grid_oracle()
    requirements = combined_requirement_oracle()
    replays = complete_replay_oracle()
    runner = runner_smoke_oracle()
    findings = malformed_definition_probe()
    request_findings = malformed_request_probe()
    files = ('blacklight/engine.py', 'combatants/actions.py',
             'combatants/modular_duel.py', 'combatants/runner.py',
             'tests/test_modular_states.py')
    hashes = {name: sha256((ROOT / name).read_bytes()).hexdigest() for name in files}
    print(json.dumps({'equivalence': 'pass', 'state_grid': states,
                      'state_transitions': transitions,
                      'combined_requirement_cases': requirements,
                      'complete_replays': replays,
                      'runner_smoke_cases': runner,
                      'malformed_definition_probe': findings,
                      'malformed_request_probe': request_findings,
                      'source_sha256': hashes}, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
