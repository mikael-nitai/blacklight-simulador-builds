"""Check a trace against its declared table revision without executing it."""

from .rulesets import CURRENT_RULESET, LEGACY_RULESET, SUPPORTED_RULESETS


def audit_ruleset_log(log, ruleset):
    if ruleset not in SUPPORTED_RULESETS:
        raise ValueError(f'Unsupported table ruleset for audit: {ruleset!r}')
    issues = []
    for event in log:
        kind, seq = event.get('type'), event.get('seq')
        if ruleset == LEGACY_RULESET and kind in ('fast_use_start', 'fast_limb_check',
                                                  'fast_limb_start', 'fast_use_end'):
            issues.append(f'event {seq}: ruleset {ruleset} contains current Fast events')
        if kind != 'attack':
            continue
        mode = event.get('mode')
        if not isinstance(mode, str):
            issues.append(f'event {seq}: ruleset attack mode is missing')
            continue
        fast = mode == 'fast_strikes' or mode.endswith('_fast')
        if event.get('damage_model') != 'literal_marvel_pool_v2':
            issues.append(f'event {seq}: ruleset damage model mismatch')
        if fast and ruleset == CURRENT_RULESET:
            if type(event.get('fast_use_id')) is not int or event.get('fast_zero_dice_bonus') is not True:
                issues.append(f'event {seq}: ruleset {ruleset} requires two-check Fast events')
        elif fast and ruleset == LEGACY_RULESET:
            if 'fast_use_id' in event or event.get('fast_zero_dice_bonus', False) is not False:
                issues.append(f'event {seq}: ruleset {ruleset} requires historical Fast events')
        expected_denominator = 2 if fast and not event.get('fantastic') else 1
        if (type(event.get('damage_denominator')) is not int
                or event['damage_denominator'] != expected_denominator
                or event.get('default_fantastic_multiplier') is not (not fast)):
            issues.append(f'event {seq}: ruleset damage event convention mismatch')
    return issues
