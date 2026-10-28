"""Independently reconcile two-combatant summaries with their event ledger."""

from .turn_audit import audit_turn_sequence


def audit_battle_result(result, profiles, *, expected_seed, max_rounds):
    profiles = tuple(profiles)
    if len(profiles) != 2 or len({p.name for p in profiles}) != 2:
        raise ValueError('A physical duel result audit needs two distinct profiles')
    names = [p.name for p in profiles]
    health = {p.name: p.max_health for p in profiles}
    focus = {p.name: p.max_focus for p in profiles}
    keys = ('damage_dealt', 'damage_taken', 'damage_mitigated', 'healing_effective',
            'focus_spent', 'attacks', 'hits', 'fantastic_hits', 'ripostes',
            'stuns_applied', 'blade_bonus_actions', 'damage_round3', 'damage_round5', 'damage_round10')
    metrics = {name: dict.fromkeys(keys, 0) for name in names}
    turns, rounds, bonus = 0, 0, False
    issues = audit_turn_sequence(result.log, profiles, outcome=result.outcome)
    for event in result.log:
        kind, actor = event.get('type'), event.get('actor')
        round_number = event.get('round')
        if type(round_number) is int:
            rounds = max(rounds, round_number)
        if kind == 'initiative' and event.get('fantastic') is True:
            bonus = True
        if kind == 'turn_start':
            turns += 1
        if kind == 'attack' and actor in metrics and event.get('target') in metrics:
            target = event['target']
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
        elif kind == 'condition_start' and event.get('condition') == 'stunned':
            source = event.get('expires_on_actor')
            if source in metrics:
                metrics[source]['stuns_applied'] += 1

    if result.seed != expected_seed:
        issues.append('result seed mismatch')
    if tuple(result.final_health) != tuple(health[name] for name in names):
        issues.append('result final Health mismatch')
    if tuple(result.final_focus) != tuple(focus[name] for name in names):
        issues.append('result final Focus mismatch')
    if result.rounds != rounds or result.turns != turns or result.bonus_round_occurred is not bonus:
        issues.append('result round/turn/bonus summary mismatch')
    alive = [name for name in names if health[name] > 0]
    if len(alive) == 2:
        expected_outcome, expected_winner = 'inconclusive', None
        if rounds != max_rounds:
            issues.append('result inconclusive before the declared round limit')
    elif len(alive) == 1:
        expected_outcome, expected_winner = 'win', alive[0]
    else:
        expected_outcome, expected_winner = 'draw', None
    if (result.outcome, result.winner) != (expected_outcome, expected_winner):
        issues.append('result winner/outcome inconsistent with final Health')
    if len(result.metrics) != 2:
        issues.append('result metrics count mismatch')
    else:
        for name, actual in zip(names, result.metrics):
            for key, expected in metrics[name].items():
                if actual.get(key) != expected:
                    issues.append(f'result metric mismatch for {name}: {key}')
    return issues
