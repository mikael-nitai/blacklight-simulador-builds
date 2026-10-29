"""Independent trace audit for the narrowly scoped Slow-Motion duel."""

from blacklight.audit import audit_profiled_log
from blacklight.result_audit import audit_battle_result
from blacklight.rulesets import CURRENT_RULESET
from blacklight.spatial_audit import audit_open_field_distance


def audit_slow_motion_duel(result, profiles, *, seed, max_rounds, initial_distance):
    profiles = tuple(profiles)
    if len(profiles) != 2 or len({p.name for p in profiles}) != 2:
        raise ValueError('Two distinct combatants are required')
    names = {p.name: p for p in profiles}
    for p in profiles:
        if (p.powers - {'slow_motion_dodge', 'accuracy', 'brawling'}
                or p.traits - {'combat_reflexes'} or p.weapons or not p.heroic):
            raise ValueError('Profile outside this audit scope')
    issues = audit_profiled_log(result.log, profiles, ruleset=CURRENT_RULESET)
    issues += audit_battle_result(result, profiles, expected_seed=seed, max_rounds=max_rounds)
    issues += audit_open_field_distance(result.log, initial_distance)
    dodging = dict.fromkeys(names, False)
    log = result.log
    for i, event in enumerate(log):
        kind, actor, seq = event.get('type'), event.get('actor'), event.get('seq')
        if kind == 'dodge' and actor in names:
            dodging[actor] = True
        elif kind == 'dodge_end' and actor in names:
            dodging[actor] = False
        elif kind == 'reaction_spent':
            if (event.get('source') != 'slow_motion_dodge' or i + 1 >= len(log)
                    or log[i + 1].get('type') != 'slow_motion_dodge'):
                issues.append(f'event {seq}: unexpected or unpaired reaction')
        elif kind == 'slow_motion_dodge':
            previous = log[i - 1] if i else {}
            following = log[i + 1] if i + 1 < len(log) else {}
            p = names.get(actor)
            if (p is None or 'slow_motion_dodge' not in p.powers or 'brawling' in p.powers
                    or previous.get('type') != 'reaction_spent' or previous.get('actor') != actor
                    or previous.get('source') != 'slow_motion_dodge'
                    or previous.get('trigger') != event.get('trigger')
                    or following.get('type') != 'attack' or following.get('mode') != 'ranged'
                    or following.get('actor') != event.get('attacker')
                    or following.get('target') != actor
                    or following.get('trigger') != event.get('trigger')
                    or event.get('before_roll') is not True
                    or type(event.get('added_troubles')) is not int
                    or event.get('added_troubles') != 1):
                issues.append(f'event {seq}: illegal or unpaired Slow-Motion Dodge')
        elif kind == 'attack':
            attacker, target = names.get(actor), names.get(event.get('target'))
            if attacker is None or target is None:
                continue
            ranged = event.get('mode') == 'ranged'
            distance = event.get('distance')
            extra = int(i > 0 and log[i - 1].get('type') == 'slow_motion_dodge')
            expected = int(dodging[target.name]) + extra
            if ranged and type(distance) is int:
                expected += int(distance > attacker.ranged_range)
            if type(event.get('troubles')) is not int or event['troubles'] != expected:
                issues.append(f'event {seq}: attack trouble sources do not match trace')
    return issues
