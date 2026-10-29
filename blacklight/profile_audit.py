"""Check trace facts against declared profiles, independently of the engine.

This is a separate ledger, not a call to combat or damage resolution. It covers
the physical-duel profile fields listed here; it is not a complete rules audit.
"""

from .dice_audit import audit_rerolls


def _bonus_candidates(profile, weapon):
    if weapon == 'ranged':
        return [profile.ranged_bonus]
    bonus = profile.melee_bonus
    if weapon in ('blade', 'claw', 'hammer'):
        extra = 2 if weapon == 'hammer' else 1
        return [bonus + extra] if 'mighty' in profile.powers else [bonus, extra]
    return [bonus]


def audit_profile_facts(log, profiles, *, allow_experimental_parry=False) -> list[str]:
    """Verify attack inputs using profiles and visible stance/shield events."""
    by_name = {profile.name: profile for profile in profiles}
    stance = dict.fromkeys(by_name, False)
    shield = {profile.name: profile.shield_active for profile in profiles}
    issues = []
    modes = {'melee', 'ranged', 'fast_strikes', 'blade', 'claw', 'hammer',
             'blade_fast', 'claw_fast', 'hammer_fast'}
    for event in log:
        kind, actor, seq = event.get('type'), event.get('actor'), event.get('seq')
        profile = by_name.get(actor)
        if kind == 'stance' and profile is not None:
            if 'attack_stance' not in profile.powers or event.get('active') is not True:
                issues.append(f'event {seq}: profile does not permit attack stance')
            stance[actor] = True
        elif kind == 'shield_activate' and profile is not None:
            if 'shield' not in profile.weapons:
                issues.append(f'event {seq}: profile does not have a shield')
            shield[actor] = True
        elif kind == 'shield_deactivate' and profile is not None:
            shield[actor] = False
        elif kind == 'condition_start' and event.get('condition') == 'stunned' and actor in stance:
            stance[actor] = False
        elif kind == 'knockback' and event.get('target') in stance:
            stance[event['target']] = False
        elif kind == 'initiative' and profile is not None:
            modifier = (profile.initiative_modifier if profile.initiative_modifier is not None
                        else profile.vigilance)
            if type(event.get('modifier')) is not int or event['modifier'] != modifier:
                issues.append(f'event {seq}: profile initiative modifier mismatch')
            issues.extend(audit_rerolls(event, edges=int('situational_awareness' in profile.traits), troubles=0))
            roll = event.get('roll')
            if (isinstance(roll, (tuple, list)) and len(roll) == 3
                    and all(type(face) is int and 1 <= face <= 6 for face in roll)):
                total = roll[0] + (6 if roll[1] == 1 else roll[1]) + roll[2] + modifier
                if event.get('total') != total or event.get('fantastic') is not (roll[1] == 1):
                    issues.append(f'event {seq}: profile initiative result mismatch')
        elif kind == 'condition_treatment' and profile is not None:
            if (type(event.get('check_modifier')) is not int
                    or event['check_modifier'] != profile.logic
                    or event.get('target_number') != 10):
                issues.append(f'event {seq}: profile treatment check mismatch')
        elif kind == 'attack':
            target = by_name.get(event.get('target'))
            if profile is None or target is None or actor == event.get('target'):
                issues.append(f'event {seq}: attack references unknown or identical profiles')
                continue
            mode = event.get('mode')
            if mode not in modes:
                issues.append(f'event {seq}: unsupported physical attack mode')
                continue
            ranged = mode == 'ranged'
            fast = mode == 'fast_strikes' or mode.endswith('_fast')
            primary = mode[:-5] if mode.endswith('_fast') else mode
            weapon = (primary if primary in ('blade', 'claw', 'hammer', 'ranged')
                      else 'bare')
            offhand = event.get('offhand')
            if ((weapon in ('blade', 'claw', 'hammer') and weapon not in profile.weapons)
                    or (offhand is not None and (not fast or offhand not in profile.weapons
                                                or offhand not in ('blade', 'claw', 'hammer')))
                    or (fast and 'fast_strikes' not in profile.powers)
                    or (event.get('reaction') and not (
                        allow_experimental_parry and event.get('reaction_power') == 'point_blank_parry'
                        and ranged and 'point_blank_parry' in profile.powers) and
                        ('riposte' not in profile.powers or ranged or fast))):
                issues.append(f'event {seq}: attack not supported by profile capabilities')
            distance = event.get('distance')
            if (type(distance) is not int or distance < 1
                    or ranged and (profile.ranged_range < 1 or distance > 2 * profile.ranged_range)
                    or not ranged and distance != 1):
                issues.append(f'event {seq}: attack exceeds profile range')
            modifier = profile.agility if ranged else profile.melee
            defense = (target.agility_defense if ranged and 'brawling' not in target.powers
                       else target.melee_defense)
            if type(event.get('check_modifier')) is not int or event['check_modifier'] != modifier:
                issues.append(f'event {seq}: profile attack modifier mismatch')
            if type(event.get('target_number')) is not int or event['target_number'] != defense:
                issues.append(f'event {seq}: profile target defense mismatch')
            if type(event.get('rank')) is not int or event['rank'] != profile.rank:
                issues.append(f'event {seq}: profile rank mismatch')
            ability = modifier * (2 if stance[actor] and not ranged else 1)
            if type(event.get('ability_for_damage')) is not int or event['ability_for_damage'] != ability:
                issues.append(f'event {seq}: profile damage ability mismatch')
            if event.get('bonus_candidates') != _bonus_candidates(profile, weapon):
                issues.append(f'event {seq}: profile weapon bonus mismatch')
            for component in event.get('damage_components', ()):
                if component.get('bonus_candidates') != _bonus_candidates(profile, component.get('weapon')):
                    issues.append(f'event {seq}: profile component weapon bonus mismatch')
            shield_applies = shield[target.name] and (not ranged or target.rank >= 2)
            reduction = target.health_dr + (2 if shield_applies else 0)
            if type(event.get('reduction')) is not int or event['reduction'] != reduction:
                issues.append(f'event {seq}: profile reduction mismatch')
            immune = bool(ranged and shield[target.name] and target.rank >= 3
                          and profile.ranged_is_ammunition)
            if type(event.get('ammunition_immunity')) is not bool or event['ammunition_immunity'] != immune:
                issues.append(f'event {seq}: profile ammunition immunity mismatch')
            before, damage, after = (event.get('health_before'), event.get('calculated_damage'),
                                     event.get('health_after'))
            if all(type(value) is int for value in (before, damage, after)):
                expected_after = before - damage
                if event.get('success') and profile.heroic and expected_after <= -target.max_health:
                    expected_after = -target.max_health + 1
                if after != expected_after:
                    issues.append(f'event {seq}: applied damage does not follow profile Heroic rule')
            if type(event.get('health_after')) is int and event['health_after'] <= 0:
                stance[target.name] = False
    return issues
