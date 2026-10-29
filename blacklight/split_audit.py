"""Independent chronology/effect ledger for the table's two-check Fast Strikes.

No production action, check, damage or effect resolver is imported here.
"""


def audit_split_fast(log) -> list[str]:
    issues = []
    uses = {}
    open_use = None
    active_limb = None
    pending_effects = []
    bonus_sources = set()
    trigger_owners = {}
    pending_bonus = {}
    last_standard_attack = {}
    for event in log:
        kind, seq = event['type'], event['seq']
        turn_key = (event.get('actor'), event.get('round'), event.get('bonus_round'))
        identity = event.get('fast_use_id')
        use = uses.get(identity) if type(identity) is int else None
        if kind == 'fast_use_start':
            weapons = event.get('weapons')
            targets = event.get('targets', [event.get('target')] * 2)
            selected = event.get('effect_limb')
            if (type(identity) is not int or identity < 1 or identity in uses
                    or open_use is not None or not isinstance(weapons, list) or len(weapons) != 2
                    or any(item not in ('bare', 'blade', 'claw', 'hammer') for item in weapons)
                    or type(selected) is not int or selected not in (0, 1)
                    or type(event.get('bonus_action')) is not bool):
                issues.append(f'event {seq}: invalid Fast declaration')
                continue
            if (not isinstance(targets, list) or len(targets) != 2
                    or any(not isinstance(target, str) or not target or target == event['actor']
                           for target in targets) or targets[0] != event.get('target')):
                issues.append(f'event {seq}: invalid predeclared Fast targets')
                continue
            uses[identity] = {'actor': event['actor'], 'target': event['target'],
                              'targets': targets,
                              'weapons': weapons, 'selected': selected,
                              'checks': [], 'attacks': [], 'closed': False,
                              'eligible': False, 'queued': set()}
            expected_bonus = turn_key in pending_bonus
            if event['bonus_action'] != expected_bonus:
                issues.append(f'event {seq}: Fast action cost/bonus declaration mismatch')
            pending_bonus.pop(turn_key, None)
            open_use = identity
        elif kind == 'fast_limb_check':
            limb = event.get('limb')
            if (use is None or open_use != identity or use['closed']
                    or type(limb) is not int or limb != len(use['checks']) or limb not in (0, 1)
                    or use['attacks'] or event.get('actor') != use['actor']
                    or event.get('target') != use['targets'][limb]
                    or event.get('weapon') != use['weapons'][limb]):
                issues.append(f'event {seq}: invalid pre-resolution limb check')
                continue
            if use['checks']:
                first = use['checks'][0]
                fields = (('modifier', 'target_number', 'edges', 'troubles')
                          if use['targets'][0] == use['targets'][1] else ('modifier',))
                if any(first[key] != event.get(key) for key in fields):
                    issues.append(f'event {seq}: checks did not use the same pre-effect state')
                if first['trigger'] == event.get('trigger'):
                    issues.append(f'event {seq}: limbs reused a hit-check trigger')
            use['checks'].append(event)
            trigger_owners[event['trigger']] = identity
        elif kind == 'fast_limb_start':
            limb = event.get('limb')
            if (use is None or open_use != identity or active_limb is not None
                    or len(use['checks']) != 2 or type(limb) is not int
                    or limb != len(use['attacks']) or limb not in (0, 1)
                    or event.get('weapon') != use['weapons'][limb]
                    or event.get('actor') != use['actor']):
                issues.append(f'event {seq}: limb resolution preceded both checks or changed order')
                continue
            active_limb, pending_effects = limb, []
        elif kind in ('condition_start', 'limb_effect') and open_use is not None:
            current = uses[open_use]
            if len(current['checks']) != 2:
                issues.append(f'event {seq}: weapon effect before both checks')
            if active_limb is not None:
                if kind == 'condition_start' and event.get('actor') == current['targets'][active_limb]:
                    pending_effects.append(('condition', event.get('condition')))
                elif (kind == 'limb_effect' and event.get('actor') == current['actor']
                      and event.get('target') == current['targets'][active_limb]):
                    pending_effects.append(('limb', 'disabled'))
                else:
                    issues.append(f'event {seq}: Fast effect used a different limb target')
        elif kind == 'reaction_spent' and open_use is not None:
            current = uses[open_use]
            if len(current['checks']) != 2:
                issues.append(f'event {seq}: reaction before both checks')
            if 'POW-06' in event.get('rules', []):
                issues.append(f'event {seq}: Riposte before both damage/effect resolutions')
            if 'CORE-P112-PARRY' in event.get('rules', []):
                issues.append(f'event {seq}: Point-Blank Parry before both damage/effect resolutions')
            if 'HR-04' in event.get('rules', []) and (current['attacks'] or active_limb is not None):
                issues.append(f'event {seq}: Shield reaction after limb damage resolution began')
        elif kind == 'shield_activate' and event.get('cost') == 'reaction' and open_use is not None:
            current = uses[open_use]
            if len(current['checks']) != 2 or current['attacks'] or active_limb is not None:
                issues.append(f'event {seq}: Shield activation outside the pre-damage window')
        elif kind == 'reaction_queued':
            trigger = event.get('trigger')
            owner = trigger_owners.get(trigger) if type(trigger) is int else None
            if open_use is not None:
                current = uses[open_use]
                attacks = current['attacks']
                if (len(current['checks']) != 2 or owner != open_use or not attacks
                        or attacks[-1]['trigger'] != trigger or attacks[-1]['success']
                        or event.get('actor') != attacks[-1]['target']
                        or event.get('source') != current['actor'] or trigger in current['queued']):
                    issues.append(f'event {seq}: reaction queued without a resolved failed limb')
                else:
                    current['queued'].add(trigger)
            elif owner is not None:
                issues.append(f'event {seq}: limb reaction queued after its Fast use ended')
        elif kind == 'attack':
            if identity is None:
                if open_use is not None:
                    issues.append(f'event {seq}: another attack interrupted the joint Fast resolution')
                if not event.get('reaction'):
                    last_standard_attack[turn_key] = event
                    pending_bonus.pop(turn_key, None)
                continue
            limb = event.get('limb')
            if (use is None or open_use != identity or active_limb != limb
                    or type(limb) is not int or limb not in (0, 1)
                    or len(use['checks']) != 2):
                issues.append(f'event {seq}: Fast limb lacks a complete declaration/check plan')
                continue
            selected = limb == use['selected']
            weapon = use['weapons'][limb]
            mode = 'fast_strikes' if weapon == 'bare' else f'{weapon}_fast'
            if (event.get('effect_limb') != use['selected']
                    or type(event.get('effects_enabled')) is not bool
                    or event['effects_enabled'] != selected
                    or event.get('actor') != use['actor'] or event.get('target') != use['targets'][limb]
                    or event.get('mode') != mode or event.get('offhand') is not None
                    or event.get('reaction') is not False or 'HR-09' not in event.get('rules', [])):
                issues.append(f'event {seq}: Fast limb changed the predeclared effect/weapon choice')
            if event.get('fast_zero_dice_bonus') is not True:
                issues.append(f'event {seq}: Fast limb omitted the current damage convention')
            check = use['checks'][limb]
            fields = ('trigger', 'roll', 'rerolls', 'target_number', 'edges', 'troubles',
                      'total', 'success', 'fantastic', 'ultimate')
            if (any(event.get(key) != check.get(key) for key in fields)
                    or event.get('check_modifier') != check.get('modifier')):
                issues.append(f'event {seq}: limb result differs from its prepared check')
            expected_effects = []
            if selected and event['success']:
                if weapon == 'blade' or weapon == 'claw' and event['fantastic']:
                    expected_effects.append(('condition', 'bleeding'))
                if weapon == 'blade' and event['fantastic']:
                    expected_effects.append(('limb', 'disabled'))
                if weapon == 'hammer' and event['fantastic']:
                    expected_effects.append(('condition', 'stunned'))
            if sorted(pending_effects) != sorted(expected_effects):
                issues.append(f'event {seq}: wrong effects for the selected limb/result')
            use['attacks'].append(event)
            active_limb, pending_effects = None, []
        elif kind == 'fast_use_end':
            if (use is None or open_use != identity or active_limb is not None
                    or len(use['checks']) != 2 or len(use['attacks']) != 2
                    or event.get('completed_limbs') != 2 or event.get('actor') != use['actor']):
                issues.append(f'event {seq}: incomplete joint Fast resolution')
                continue
            selected_attack = use['attacks'][use['selected']]
            if use['queued'] != {attack['trigger'] for attack in use['attacks'] if not attack['success']}:
                issues.append(f'event {seq}: missing or surplus failed-limb reaction queue')
            eligible = (use['weapons'][use['selected']] == 'blade'
                        and selected_attack['success'] and selected_attack['fantastic'])
            if (type(event.get('blade_bonus_eligible')) is not bool
                    or event['blade_bonus_eligible'] != eligible):
                issues.append(f'event {seq}: Blade bonus eligibility used the wrong limb')
            use['closed'], use['eligible'], open_use = True, eligible, None
        elif kind == 'blade_bonus' and 'source_fast_use' in event:
            source = event['source_fast_use']
            if source is None:
                parent = last_standard_attack.get(turn_key)
                if (parent is None or parent.get('mode') != 'blade'
                        or not parent.get('success') or not parent.get('fantastic')):
                    issues.append(f'event {seq}: Blade bonus lacks a successful standard Blade Fantastic')
            else:
                parent = uses.get(source) if type(source) is int else None
                if (parent is None or not parent['closed'] or not parent['eligible']
                        or parent['actor'] != event.get('actor') or source in bonus_sources):
                    issues.append(f'event {seq}: Blade bonus lacks an eligible selected-limb source')
                if type(source) is int:
                    bonus_sources.add(source)
            pending_bonus[turn_key] = True
    if open_use is not None or any(not use['closed'] for use in uses.values()):
        issues.append('Incomplete Fast use at end of trace')
    if pending_bonus:
        issues.append('Declared Blade bonus was not resolved')
    return issues
