"""Independently verify experimental end-turn healing, bleeding and death."""


def audit_incapacity_endturn(log, profiles, *, healing_first, self_damage_mode):
    """Compare automatic end-turn events with a reconstructed health ledger."""
    profiles = tuple(profiles)
    if (len(profiles) != 2 or profiles[0].name == profiles[1].name
            or type(healing_first) is not bool
            or self_damage_mode not in ('lethal_impact', 'nonlethal_impact')):
        raise ValueError('Invalid end-turn audit contract')
    by_name = {profile.name: profile for profile in profiles}
    health = {profile.name: profile.max_health for profile in profiles}
    bleeding = dict.fromkeys(by_name, 0)
    active, start, actual, issues = None, None, [], []

    def expected_end(name, hp, bleed):
        profile = by_name[name]
        rows = []

        def death():
            if hp <= -profile.max_health:
                rows.append(('incapacity_dead', {'health': hp, 'mode': self_damage_mode}))
                return True
            return False

        def heal():
            nonlocal hp, bleed
            if 'healing_factor' not in profile.powers:
                return
            before = hp
            hp = min(profile.max_health, hp + profile.resilience)
            effective = hp - before
            if effective >= 1 and bleed:
                rows.append(('condition_end', {'condition': 'bleeding', 'prior_intensity': bleed}))
                bleed = 0
            rows.append(('heal', {'proposed': profile.resilience, 'effective': effective,
                                  'health_before': before, 'health_after': hp}))

        if death():
            return rows
        if healing_first:
            heal()
        if bleed:
            before = hp
            damage = max(0, bleed - 5 * profile.health_dr)
            hp -= damage
            rows.append(('condition_tick', {'condition': 'bleeding', 'intensity': bleed,
                                            'damage': damage, 'health_before': before, 'health_after': hp}))
        if death():
            return rows
        if not healing_first:
            heal()
        return rows

    for event in log:
        kind, actor, seq = event.get('type'), event.get('actor'), event.get('seq')
        if kind == 'turn_start':
            if not isinstance(actor, str) or actor not in by_name:
                issues.append(f'event {seq}: unknown turn actor')
                active, start, actual = None, None, []
            else:
                active, start, actual = actor, None, []
        if active is not None:
            rules = event.get('rules', ())
            if not isinstance(rules, (tuple, list)):
                issues.append(f'event {seq}: invalid rule references')
                rules = ()
            automatic_heal = kind == 'heal' and 'POW-03' in rules
            automatic_clear = (kind == 'condition_end' and event.get('condition') == 'bleeding'
                               and 'POW-03' in rules)
            tick = kind == 'condition_tick' and event.get('condition') == 'bleeding'
            death_marker = kind == 'incapacity_dead'
            shield_tail = (kind == 'reaction_spent' and event.get('source') == 'end_turn'
                           or kind == 'shield_activate' and event.get('timing') == 'end_turn')
            if (automatic_heal or automatic_clear or tick or death_marker or shield_tail) and actor != active:
                issues.append(f'event {seq}: automatic end-turn event has wrong actor')
            if (automatic_heal or automatic_clear or tick or death_marker or shield_tail) and start is None:
                start = (health[active], bleeding[active])
            if (start is not None and kind in ('attack', 'ram_attack', 'movement', 'fast_use_start',
                                               'stance', 'dodge', 'wait', 'focus_spent', 'condition_treatment')):
                issues.append(f'event {seq}: action after automatic end-turn effects began')
            if automatic_heal or automatic_clear or tick or death_marker:
                actual.append(event)
            if kind == 'turn_end':
                if actor != active:
                    issues.append(f'event {seq}: end-turn actor mismatch')
                start = start if start is not None else (health[active], bleeding[active])
                expected = expected_end(active, *start)
                if len(actual) != len(expected):
                    issues.append(f'event {seq}: missing or extra automatic end-turn effects')
                else:
                    for got, (expected_kind, fields) in zip(actual, expected):
                        if (got.get('type') != expected_kind
                                or any(type(got.get(key)) is not type(value) or got.get(key) != value
                                       for key, value in fields.items())):
                            issues.append(f'event {got.get("seq")}: incorrect automatic end-turn effect')
                active, start, actual = None, None, []
        if kind == 'attack' and event.get('target') in health:
            health[event['target']] = event.get('health_after')
        elif kind == 'ram_attack' and actor in health and event.get('target') in health:
            health[actor] = event.get('attacker_health_after')
            health[event['target']] = event.get('target_health_after')
        elif kind in ('heal', 'condition_tick') and actor in health:
            health[actor] = event.get('health_after')
        if kind == 'condition_start' and event.get('condition') == 'bleeding' and actor in bleeding:
            bleeding[actor] = event.get('intensity')
        elif kind == 'condition_end' and event.get('condition') == 'bleeding' and actor in bleeding:
            bleeding[actor] = 0
        elif kind == 'condition_treatment' and actor in bleeding and event.get('condition') == 'bleeding':
            bleeding[actor] = event.get('remaining_intensity')
    if active is not None:
        issues.append('Experimental duel ended with an open turn')
    return issues
