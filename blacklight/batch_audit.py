"""Recheck a recorded generic batch's seeds and audit coverage independently."""

from hashlib import sha256
import json
from math import isclose, isfinite, sqrt

from .rulesets import CURRENT_RULESET, LEGACY_RULESET
from .extended_batch_audit import audit_extended_batch


def _wilson_95(count, total):
    # Independent closed-form check of the runner's 95% Wilson interval.
    z = 1.959963984540054
    proportion = count / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    half_width = z * sqrt(proportion * (1 - proportion) / total
                          + z * z / (4 * total * total)) / denominator
    return max(0.0, center - half_width), min(1.0, center + half_width)


def audit_batch_metadata(payload):
    issues = []
    n, interval, master = payload.get('n'), payload.get('audit_every'), payload.get('master_seed')
    traces = payload.get('audited_traces')
    if (type(n) is not int or n < 1 or type(interval) is not int or interval < 1
            or type(master) is not int or payload.get('audit_scope') != 'all_starts'
            or not isinstance(traces, list) or len(traces) != n
            or n > 1 and interval != 1):
        return ['batch audit does not cover all starts']
    try:
        cell = {name: payload[name] for name in ('sheets', 'policies', 'initial_distance', 'max_rounds')}
        if payload.get('battlefield') is not None:
            cell['battlefield'] = payload['battlefield']
        if payload.get('table_ruleset') == CURRENT_RULESET:
            version = 'character-batch-v2'
            cell['policy_types'] = payload['policy_types']
        elif payload.get('table_ruleset') == LEGACY_RULESET:
            version = 'character-batch-v1'
        else:
            return ['batch audit has an unknown ruleset']
        cell_hash = sha256(json.dumps(cell, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        formula = f'first 8 SHA-256 bytes of {version}|master_seed|cell_sha256|index'
        if payload.get('cell_sha256') != cell_hash or payload.get('seed_formula') != formula:
            issues.append('batch audit cell or seed formula mismatch')
        for index, trace in enumerate(traces):
            key = f'{version}|{master}|{cell_hash}|{index}'
            seed = int.from_bytes(sha256(key.encode()).digest()[:8], 'big')
            if (not isinstance(trace, dict) or trace.get('index') != index
                    or type(trace.get('index')) is not int or type(trace.get('seed')) is not int
                    or trace['seed'] != seed or trace.get('issues') != []):
                issues.append(f'batch audit missing, invalid or misidentified trace {index}')
                break
        outcomes, rates = payload['outcomes'], payload['rates']
        outcomes_expected = {'win', 'loss', 'draw', 'inconclusive'}
        if (not isinstance(outcomes, dict) or set(outcomes) != outcomes_expected
                or any(type(count) is not int or count < 0 for count in outcomes.values())
                or sum(outcomes.values()) != n):
            issues.append('batch audit outcome totals mismatch')
        elif not isinstance(rates, dict) or set(rates) != outcomes_expected:
            issues.append('batch audit rate fields mismatch')
        else:
            for name, count in outcomes.items():
                estimate = rates[name].get('estimate') if isinstance(rates[name], dict) else None
                if (type(estimate) not in (int, float) or not isfinite(estimate)
                        or not isclose(estimate, count / n, rel_tol=0, abs_tol=1e-12)):
                    issues.append(f'batch audit outcome rate mismatch: {name}')
                interval = rates[name].get('wilson95') if isinstance(rates[name], dict) else None
                expected = _wilson_95(count, n)
                if (not isinstance(interval, (list, tuple)) or len(interval) != 2
                        or any(type(value) not in (int, float) or not isfinite(value)
                               or not isclose(value, reference, rel_tol=0, abs_tol=1e-12)
                               for value, reference in zip(interval, expected))):
                    issues.append(f'batch audit Wilson interval mismatch: {name}')
    except (KeyError, TypeError, ValueError):
        issues.append('batch audit metadata is incomplete or invalid')
    issues.extend(audit_extended_batch(payload))
    return issues
