"""Audit the explicit weaponless nonlethal experiment against the original profiles."""

from dataclasses import replace

from .ram_prone_audit import audit_ram_prone_duel


def audit_nonlethal_ram_duel(result, profiles, *, declared_armed_lethal=(), **context):
    """Check the unarmed floor, then reuse existing experimental duel ledgers."""
    profiles = tuple(profiles)
    if len(profiles) != 2 or profiles[0].name == profiles[1].name:
        raise ValueError('Exactly two distinct profiles are required')
    if not isinstance(result.log, (tuple, list)) or any(not isinstance(event, dict) for event in result.log):
        return ['Invalid nonlethal experimental log']
    names = {profile.name: profile for profile in profiles}
    if (not isinstance(declared_armed_lethal, tuple)
            or any(not isinstance(name, str) or name not in names for name in declared_armed_lethal)
            or len(set(declared_armed_lethal)) != len(declared_armed_lethal)):
        raise ValueError('Declared lethal actors must be a tuple of distinct combatant names')
    issues = []
    for event in result.log:
        if event.get('type') != 'attack':
            continue
        actor, target, seq = event.get('actor'), event.get('target'), event.get('seq')
        if not isinstance(actor, str) or not isinstance(target, str) or actor not in names or target not in names:
            issues.append(f'event {seq}: invalid nonlethal attack identity')
            continue
        p, q = names[actor], names[target]
        bare = event.get('mode') in ('melee', 'fast_strikes') and event.get('offhand') is None
        qualified = bare and not p.heroic and not p.weapons and not p.ranged_range
        if (bare and not p.heroic and (p.weapons or p.ranged_range)
                and (actor not in declared_armed_lethal or event.get('declared_lethality') != 'lethal')):
            issues.append(f'event {seq}: armed profile has an unresolved bare attack')
        keys = ('nonlethal_floor', 'nonlethal_raw_after', 'nonlethal_prevented')
        if not qualified:
            if any(key in event for key in keys):
                issues.append(f'event {seq}: nonlethal marker on an unsupported attack')
            continue
        if (type(event.get('health_before')) is not int or type(event.get('health_after')) is not int
                or type(event.get('calculated_damage')) is not int or type(event.get('damage')) is not int
                or type(event.get('success')) is not bool):
            issues.append(f'event {seq}: invalid nonlethal damage facts')
            continue
        raw = event['health_before'] - event['calculated_damage']
        floor = -q.max_health + 1
        capped = event['success'] and raw <= -q.max_health
        expected = max(floor, raw) if capped else raw
        if event['health_after'] != expected or event['damage'] != event['health_before'] - expected:
            issues.append(f'event {seq}: default nonlethal damage floor mismatch')
        if capped:
            if (any(type(event.get(key)) is not int for key in keys)
                    or event['nonlethal_floor'] != floor or event['nonlethal_raw_after'] != raw
                    or event['nonlethal_prevented'] != floor - raw):
                issues.append(f'event {seq}: missing or inconsistent nonlethal marker')
        elif any(key in event for key in keys):
            issues.append(f'event {seq}: unexpected nonlethal marker')
    if issues:
        return issues
    # The existing profile ledger already models the identical floor for Heroic
    # attacks. A shadow profile extends that check only to actors that cannot
    # carry any modeled weapon; this does not alter the actual character sheet.
    shadow = tuple(replace(p, heroic=True) if not p.heroic and not p.weapons and not p.ranged_range else p
                   for p in profiles)
    return audit_ram_prone_duel(result, shadow, **context)
