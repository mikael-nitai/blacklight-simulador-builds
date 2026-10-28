"""Independently reconcile optional per-start combat metrics and summaries."""

from collections import Counter
from math import ceil, isclose, isfinite, sqrt


FIELDS = ('index', 'seed', 'outcome', 'rounds', 'turns', 'final_health', 'final_focus',
          'opponent_final_health', 'opponent_final_focus',
          'damage_dealt', 'damage_taken', 'damage_mitigated', 'healing_effective',
          'focus_spent', 'attacks', 'hits', 'fantastic_hits', 'ripostes',
          'stuns_applied', 'blade_bonus_actions', 'damage_round3', 'damage_round5', 'damage_round10')
EXTENDED_KEYS = frozenset(('extended_metrics_schema', 'extended_fields', 'extended_samples_all_starts',
                           'extended_metrics_all_starts', 'extended_metrics_note'))


def audit_extended_batch(payload):
    present = EXTENDED_KEYS & payload.keys()
    if not present:
        return []
    if present != EXTENDED_KEYS or payload.get('extended_metrics_schema') != 'blacklight-batch-combat-samples-v1':
        return ['unknown or incomplete extended batch metrics']
    n, samples = payload.get('n'), payload.get('extended_samples_all_starts')
    summaries = payload.get('extended_metrics_all_starts')
    if (type(n) is not int or n < 1 or payload.get('extended_fields') != list(FIELDS)
            or not isinstance(samples, list) or len(samples) != n
            or not isinstance(summaries, dict) or set(summaries) != set(FIELDS[3:])):
        return ['extended batch sample shape mismatch']
    issues = []
    outcomes = Counter()
    traces = payload.get('audited_traces')
    sheets = payload.get('sheets')
    if (not isinstance(traces, list) or len(traces) != n or not isinstance(sheets, list)
            or len(sheets) != 2 or any(not isinstance(sheet, dict) or not isinstance(sheet.get('resources'), dict)
                                       for sheet in sheets)):
        return ['extended batch requires audited starts and two resource records']
    for index, sample in enumerate(samples):
        if (not isinstance(sample, list) or len(sample) != len(FIELDS)
                or type(sample[0]) is not int or sample[0] != index or type(sample[1]) is not int
                or not isinstance(traces[index], dict) or sample[1] != traces[index].get('seed')
                or sample[2] not in ('win', 'loss', 'draw', 'inconclusive')
                or any(type(value) is not int for value in sample[3:])
                or any(value < 0 for pos, value in enumerate(sample[3:], 3)
                       if FIELDS[pos] not in ('final_health', 'opponent_final_health'))):
            return [f'extended batch invalid sample {index}']
        row = dict(zip(FIELDS, sample))
        if (type(payload.get('max_rounds')) is not int or not 0 <= row['rounds'] <= payload['max_rounds']
                or not 1 <= row['turns'] <= 2 * (row['rounds'] + 1)
                or row['hits'] > row['attacks'] or row['fantastic_hits'] > row['hits']
                or row['ripostes'] > row['attacks']
                or row['stuns_applied'] > row['fantastic_hits']
                or row['blade_bonus_actions'] > row['fantastic_hits']
                or not 0 <= row['damage_round3'] <= row['damage_round5'] <= row['damage_round10'] <= row['damage_dealt']):
            issues.append(f'extended batch impossible combat counters at sample {index}')
        try:
            initial_health = sheets[0]['resources']['health']
            initial_focus = sheets[0]['resources']['focus']
            if (row['final_health'] != initial_health - row['damage_taken'] + row['healing_effective']
                    or row['final_focus'] != initial_focus - row['focus_spent']
                    or row['final_focus'] < 1 or row['opponent_final_focus'] < 1
                    or row['final_health'] > initial_health
                    or row['opponent_final_health'] > sheets[1]['resources']['health']
                    or row['opponent_final_focus'] > sheets[1]['resources']['focus']):
                issues.append(f'extended batch resource mismatch at sample {index}')
        except (KeyError, TypeError):
            return ['extended batch invalid initial resources']
        alive, foe_alive = row['final_health'] > 0, row['opponent_final_health'] > 0
        expected_outcome = ('inconclusive' if alive and foe_alive else
                            'win' if alive else 'loss' if foe_alive else 'draw')
        if row['outcome'] != expected_outcome or (expected_outcome == 'inconclusive'
                                                   and row['rounds'] != payload.get('max_rounds')):
            issues.append(f'extended batch outcome mismatch at sample {index}')
        outcomes[sample[2]] += 1
    if not isinstance(payload.get('outcomes'), dict) or any(outcomes[name] != payload['outcomes'].get(name)
           for name in ('win', 'loss', 'draw', 'inconclusive')):
        issues.append('extended batch outcomes disagree with samples')
    for position, name in enumerate(FIELDS[3:], 3):
        values = sorted(sample[position] for sample in samples)
        mean = sum(values) / n
        se = None if n == 1 else sqrt(sum((value - mean) ** 2 for value in values) / (n - 1) / n)
        expected = {'mean': mean, 'mc_se': se,
                    **{f'q{pct}': values[ceil(n * pct / 100) - 1] for pct in (10, 50, 90)}}
        actual = summaries.get(name)
        if not isinstance(actual, dict) or set(actual) != set(expected):
            issues.append(f'extended batch missing summary for {name}')
            continue
        for key, reference in expected.items():
            value = actual.get(key)
            if reference is None:
                valid = value is None
            else:
                valid = (type(value) in (int, float) and isfinite(value)
                         and isclose(value, reference, rel_tol=1e-12, abs_tol=1e-9))
            if not valid:
                issues.append(f'extended batch inconsistent {name} {key}')
    comparisons = {'rounds': 'rounds', 'hero_final_health': 'final_health',
                   'hero_final_focus': 'final_focus', 'hero_damage_dealt': 'damage_dealt',
                   'hero_damage_taken': 'damage_taken'}
    base = payload.get('metrics_all_starts', {})
    for old, new in comparisons.items():
        if (not isinstance(base, dict) or not isinstance(base.get(old), dict)
                or not isinstance(summaries.get(new), dict)
                or any(not (base[old].get(key) is None and summaries[new].get(key) is None)
                       and (type(base[old].get(key)) not in (int, float)
                            or type(summaries[new].get(key)) not in (int, float)
                            or not isclose(base[old][key], summaries[new][key], rel_tol=1e-12, abs_tol=1e-9))
                       for key in ('mean', 'mc_se'))):
            issues.append(f'extended batch summary disagrees with existing {old}')
    return issues
