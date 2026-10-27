"""Read-only differential audit of the first modular action migration.

Run from the repository root:
    python -B -m scripts.audit_modular_healing

This compares Do This All Day against the frozen Duel resolver. It does not
estimate strategy performance, create experiment results, or modify files.
"""

from hashlib import sha256
import json
from pathlib import Path

from blacklight.engine import Action, Duel, IllegalAction, Profile, blacklight_profile
from blacklight.policies import RulePolicy
from combatants.actions import ActionPlan, ActionRegistry, CapabilityRequirement, RestoreHealth
from combatants.modular_duel import ModularDuel


ROOT = Path(__file__).resolve().parents[1]


def profile(rank: int, *, powers: frozenset[str] = frozenset({'do_this_all_day'})) -> Profile:
    return Profile('A', rank, 100, 100, 1, 1, 1, 1, 11, 11, 5, powers=powers)


def setup(cls, first: Profile, second: Profile, *, registry=None):
    options = {'seed': 7, 'audit': True}
    if registry is not None:
        options['action_registry'] = registry
    duel = cls((first, second), (None, None), **options)
    duel.active_actor = 0
    duel.fighters[0].standard_available = True
    return duel


def direct_transition_oracle() -> tuple[int, int]:
    """Compare all available heals over a deliberately broad finite state grid."""
    states = transitions = 0
    second = profile(3, powers=frozenset())
    for rank in range(1, 7):
        first = profile(rank)
        for health in (0, 1, 50, 99, 100):
            for focus in range(101):
                for bleeding in (0, 5):
                    old = setup(Duel, first, second)
                    new = setup(ModularDuel, first, second)
                    for game in (old, new):
                        fighter = game.fighters[0]
                        fighter.health = health
                        fighter.focus = focus
                        fighter.bleeding = bleeding
                    states += 1
                    actions = old.legal_actions(0)
                    if actions != new.legal_actions(0):
                        raise AssertionError(('legal_actions', rank, health, focus, bleeding))
                    for action in actions:
                        if action.kind != 'heal':
                            continue
                        old_one = setup(Duel, first, second)
                        new_one = setup(ModularDuel, first, second)
                        for game in (old_one, new_one):
                            fighter = game.fighters[0]
                            fighter.health = health
                            fighter.focus = focus
                            fighter.bleeding = bleeding
                            game._act(0, action)
                        if (vars(old_one.fighters[0]) != vars(new_one.fighters[0])
                                or old_one.log != new_one.log):
                            raise AssertionError(('transition', rank, health, focus,
                                                  bleeding, action))
                        transitions += 1
    return states, transitions


def complete_replay_oracle() -> int:
    """Use identical fixed policies and seeds only for refactor equivalence."""
    hero = blacklight_profile()
    foe = Profile('foe', 3, 120, 60, 6, 1, 4, 1, 16, 11, 5)
    policies = (RulePolicy('heal', heal_missing=15, heal_spend=15),
                RulePolicy('attack'))
    replays = 0
    for distance in (1, 5, 12):
        for seed in range(100):
            options = {'seed': seed, 'initial_distance': distance,
                       'max_rounds': 15, 'audit': True}
            old = Duel((hero, foe), policies, **options).run()
            new = ModularDuel((hero, foe), policies, **options).run()
            if old != new:
                raise AssertionError(('replay', distance, seed))
            replays += 1
    return replays


class FixtureModule:
    kind = 'fixture'
    requirements = (CapabilityRequirement('power', 'do_this_all_day'),)
    sources = ('AUDIT-ONLY',)

    def __init__(self, requests, plan_factory):
        self.requests = requests
        self.plan_factory = plan_factory

    def available(self, context):
        return self.requests

    def plan(self, context, request):
        return self.plan_factory()


def reject_without_mutation(requests, plan_factory, *, focus=90,
                            check='act') -> None:
    duel = setup(ModularDuel, profile(3), profile(3),
                 registry=ActionRegistry((FixtureModule(requests, plan_factory),)))
    fighter = duel.fighters[0]
    fighter.focus = focus
    fighter.health = 50
    before = (fighter.health, fighter.focus, fighter.focus_spent,
              fighter.standard_available, tuple(duel.log))
    try:
        if check == 'legal':
            duel.legal_actions(0)
        else:
            duel._act(0, Action('fixture', 5))
    except IllegalAction:
        pass
    else:
        raise AssertionError(('expected IllegalAction', requests, check))
    after = (fighter.health, fighter.focus, fighter.focus_spent,
             fighter.standard_available, tuple(duel.log))
    if after != before:
        raise AssertionError(('partial mutation', before, after))


def malformed_extension_oracles() -> int:
    valid_request = (Action('fixture', 5),)
    valid_effect = (RestoreHealth(10, 'AUDIT-ONLY'),)
    cases = (
        (valid_request, lambda: ActionPlan('fixture', 5, 1, ('AUDIT-ONLY',),
                                           (RestoreHealth(10, 'AUDIT-ONLY') for _ in range(1))), 90, 'act'),
        (valid_request, lambda: ActionPlan('fixture', 5, 1, ('AUDIT-ONLY',), ()), 90, 'act'),
        (valid_request, lambda: ActionPlan('fixture', 5, 1, (x for x in ()),
                                           valid_effect), 90, 'act'),
        (([],), lambda: None, 90, 'legal'),
        ((Action('wrong_kind', 5),), lambda: None, 90, 'legal'),
        ((Action('fixture', 16),), lambda: None, 90, 'legal'),
        (valid_request, lambda: None, 5, 'legal'),
    )
    for requests, plan_factory, focus, check in cases:
        reject_without_mutation(requests, plan_factory,
                                focus=focus, check=check)
    return len(cases)


def main() -> None:
    states, transitions = direct_transition_oracle()
    replays = complete_replay_oracle()
    malformed = malformed_extension_oracles()
    sources = {}
    for relative in ('blacklight/engine.py', 'combatants/actions.py',
                     'combatants/modular_duel.py'):
        sources[relative] = sha256((ROOT / relative).read_bytes()).hexdigest()
    print(json.dumps({'status': 'pass', 'state_grid': states,
                      'heal_transitions': transitions,
                      'complete_replays': replays,
                      'malformed_extension_cases': malformed,
                      'source_sha256': sources}, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
