"""Additional independent checks for experimental fixed-contact group traces.

This does not certify the complete group rules. It supplements the profiled
arithmetic and initiative audits with team, Fast check and result ledgers.
"""


def audit_group_trace(result, profiles, teams, *, seed, max_rounds):
    names = tuple(profile.name for profile in profiles)
    if (len(names) < 2 or len(set(names)) != len(names)
            or not isinstance(teams, tuple) or len(teams) != len(names)):
        raise ValueError('Group audit requires distinct names and matching teams')
    by_name = dict(zip(names, profiles))
    team = dict(zip(names, teams))
    health = {p.name: p.max_health for p in profiles}
    focus = {p.name: p.max_focus for p in profiles}
    stunned = dict.fromkeys(names, False)
    dodging = dict.fromkeys(names, False)
    metric_keys = ('damage_dealt', 'damage_taken', 'damage_mitigated', 'healing_effective',
                   'focus_spent', 'attacks', 'hits', 'fantastic_hits', 'ripostes',
                   'stuns_applied', 'blade_bonus_actions', 'damage_round3',
                   'damage_round5', 'damage_round10')
    metrics = {name: dict.fromkeys(metric_keys, 0) for name in names}
    issues, attacks, queued = [], {}, {}
    expected_reaction = None
    active = None
    turns, rounds, bonus = 0, 0, False
    for event in result.log:
        kind, actor, seq = event.get('type'), event.get('actor'), event.get('seq')
        round_number = event.get('round')
        if type(round_number) is int:
            rounds = max(rounds, round_number)
        if kind == 'initiative' and event.get('fantastic') is True:
            bonus = True
        elif kind == 'turn_start':
            if actor not in by_name or active is not None:
                issues.append(f'event {seq}: invalid or nested turn')
            active = actor
            turns += 1
        elif kind == 'turn_end':
            if actor != active:
                issues.append(f'event {seq}: unmatched turn end')
            active = None
        elif kind == 'dodge' and actor in dodging:
            dodging[actor] = True
        elif kind == 'dodge_end' and actor in dodging:
            dodging[actor] = False
        elif kind == 'condition_start' and event.get('condition') == 'stunned' and actor in stunned:
            stunned[actor] = True
            source = event.get('expires_on_actor')
            if source in metrics:
                metrics[source]['stuns_applied'] += 1
        elif kind == 'condition_end' and event.get('condition') == 'stunned' and actor in stunned:
            stunned[actor] = False
        elif kind == 'fast_use_start':
            targets = event.get('targets', [event.get('target')] * 2)
            if (actor not in team or active != actor or not isinstance(targets, list)
                    or len(targets) != 2 or any(target not in team or team[target] == team[actor]
                                               or health[target] <= 0 for target in targets)):
                issues.append(f'event {seq}: invalid or friendly Fast target')
        elif kind == 'fast_limb_check':
            target = event.get('target')
            if actor not in by_name or target not in by_name or team[actor] == team[target]:
                issues.append(f'event {seq}: invalid Fast check actor or target')
                continue
            profile = by_name[actor]
            power_edges = int('blazing_fast_fists' in profile.powers) + int(
                'signature_fast_strikes' in profile.traits)
            expected_edges = max(power_edges, int(stunned[target]))
            if (any(type(event.get(key)) is not int for key in
                    ('modifier', 'target_number', 'edges', 'troubles'))
                    or event.get('modifier') != profile.melee
                    or event.get('target_number') != by_name[target].melee_defense
                    or event.get('edges') != expected_edges
                    or event.get('troubles') != int(dodging[target])):
                issues.append(f'event {seq}: Fast check disagrees with pre-effect profile/state')
        elif kind == 'attack':
            target = event.get('target')
            if actor not in team or target not in team or team[actor] == team[target]:
                issues.append(f'event {seq}: invalid or friendly attack')
                continue
            if event.get('reaction') is not True and active != actor:
                issues.append(f'event {seq}: attack outside actor turn')
            if event.get('reaction') is True:
                if (expected_reaction != (actor, target) or health[target] <= 0
                        or health[actor] <= 0 or stunned[actor]):
                    issues.append(f'event {seq}: invalid Riposte source, target or condition')
                expected_reaction = None
            attacks[event.get('trigger')] = event
            damage = event['damage']
            metrics[actor]['damage_dealt'] += damage
            metrics[target]['damage_taken'] += damage
            metrics[actor]['attacks'] += 1
            metrics[actor]['hits'] += int(event['success'])
            metrics[actor]['fantastic_hits'] += int(event['success'] and event['fantastic'])
            metrics[actor]['ripostes'] += int(event['reaction'])
            for horizon in (3, 5, 10):
                if type(round_number) is int and round_number <= horizon:
                    metrics[actor][f'damage_round{horizon}'] += damage
            raw = sum(component.get('damage_without_reduction') or 0
                      for component in event.get('damage_components', ()))
            metrics[target]['damage_mitigated'] += max(0, raw - event['calculated_damage'])
            health[target] = event['health_after']
        elif kind == 'reaction_queued':
            trigger, source = event.get('trigger'), event.get('source')
            prior = attacks.get(trigger)
            if (prior is None or prior.get('success') is not False
                    or prior.get('actor') != source or prior.get('target') != actor):
                issues.append(f'event {seq}: reaction queue has no matching failed attack')
            else:
                queued[trigger] = (actor, source)
        elif kind == 'reaction_spent' and 'POW-06' in event.get('rules', ()):
            trigger = event.get('trigger')
            if trigger not in queued or queued[trigger][0] != actor or expected_reaction is not None:
                issues.append(f'event {seq}: Riposte spent against an invalid trigger')
            else:
                expected_reaction = queued.pop(trigger)
        elif kind == 'heal' and actor in metrics:
            metrics[actor]['healing_effective'] += event['effective']
            health[actor] = event['health_after']
        elif kind == 'condition_tick' and actor in metrics:
            metrics[actor]['damage_taken'] += event['damage']
            health[actor] = event['health_after']
        elif kind == 'focus_spent' and actor in metrics:
            metrics[actor]['focus_spent'] += event['amount']
            focus[actor] = event['focus_after']
        elif kind == 'blade_bonus' and actor in metrics:
            metrics[actor]['blade_bonus_actions'] += 1
    if active is not None:
        issues.append('group result ended with an open turn')
    if expected_reaction is not None:
        issues.append('group result ended before a spent Riposte was resolved')
    if result.seed != seed or result.teams != teams:
        issues.append('group result seed or teams mismatch')
    if result.final_health != tuple(health[name] for name in names):
        issues.append('group result final Health mismatch')
    if result.final_focus != tuple(focus[name] for name in names):
        issues.append('group result final Focus mismatch')
    if result.rounds != rounds or result.turns != turns or result.bonus_round_occurred is not bonus:
        issues.append('group result round/turn/bonus summary mismatch')
    surviving = {team[name] for name in names if health[name] > 0}
    expected = (('draw', None) if not surviving else
                ('win', next(iter(surviving))) if len(surviving) == 1 else ('inconclusive', None))
    if (result.outcome, result.winner) != expected:
        issues.append('group result winner/outcome mismatch')
    if expected[0] == 'inconclusive' and rounds != max_rounds:
        issues.append('group result inconclusive before round limit')
    if len(result.metrics) != len(names):
        issues.append('group result metric count mismatch')
    else:
        for name, actual in zip(names, result.metrics):
            for key, value in metrics[name].items():
                if actual.get(key) != value:
                    issues.append(f'group result metric mismatch for {name}: {key}')
    return issues
