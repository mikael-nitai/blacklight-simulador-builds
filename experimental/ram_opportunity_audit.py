"""Independent audit of 1D Ram opportunity markers, not Ram attack resolution."""


def audit_ram_opportunities(log, profiles):
    """Reconstruct markers from movement, health and reaction events.

    Run the existing physical and distance audits as well; this verifier assumes
    their base movement and lifecycle events are complete and valid.
    """
    profiles = tuple(profiles)
    if len(profiles) != 2 or profiles[0].name == profiles[1].name:
        raise ValueError('Exactly two distinct profiles are required')
    names = [p.name for p in profiles]
    health = {p.name: p.max_health for p in profiles}
    speed = {p.name: p.run_speed for p in profiles}
    reactions = {p.name: None for p in profiles}
    pending, expected, issues = {}, None, []
    for event in log:
        kind, actor = event.get('type'), event.get('actor')
        if expected is not None:
            if kind != 'ram_opportunity':
                issues.append(f"event {event.get('seq')}: missing Ram opportunity marker")
                expected = None
            else:
                numeric = ('first_before', 'first_after', 'second_after', 'speed', 'reactions')
                if (any(type(event.get(key)) is not int for key in numeric)
                        or any(event.get(key) != value for key, value in expected.items())):
                    issues.append(f"event {event.get('seq')}: invalid Ram opportunity marker")
                expected = None
                continue
        elif kind == 'ram_opportunity':
            issues.append(f"event {event.get('seq')}: unexpected Ram opportunity marker")
            continue
        if actor not in health:
            continue
        if kind in ('reaction_reset', 'turn_start'):
            reactions[actor] = event.get('reactions')
        elif kind == 'reaction_spent':
            reactions[actor] = event.get('remaining')
        if kind in ('turn_start', 'turn_end'):
            pending.pop(actor, None)
        if kind == 'attack' and event.get('target') in health:
            health[event['target']] = event.get('health_after')
        elif kind in ('heal', 'condition_tick'):
            health[actor] = event.get('health_after')
        if kind != 'movement':
            continue
        before, after = event.get('distance_before'), event.get('distance_after')
        if (type(before) is not int or type(after) is not int
                or event.get('direction') != 'approach' or before <= after):
            pending.pop(actor, None)
            continue
        if event.get('as_standard') is False:
            pending[actor] = (before, after, event.get('round'), event.get('bonus_round'))
        elif event.get('as_standard') is True:
            first = pending.pop(actor, None)
            other = names[1 - names.index(actor)]
            if (first is not None and first[2:] == (event.get('round'), event.get('bonus_round'))
                    and first[0] - first[1] == speed[actor] and first[1] == before and after == 1
                    and type(reactions[actor]) is int and reactions[actor] > 0
                    and type(health[actor]) is int and health[actor] > 0
                    and type(health[other]) is int and health[other] > 0):
                expected = {'actor': actor, 'target': other, 'first_before': first[0],
                            'first_after': first[1], 'second_after': after,
                            'speed': speed[actor], 'reactions': reactions[actor],
                            'scope': 'opportunity only; no reaction or attack performed'}
    if expected is not None:
        issues.append('End of log: missing Ram opportunity marker')
    return issues
