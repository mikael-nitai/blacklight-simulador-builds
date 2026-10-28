"""Identify recorded mechanical code and action parameters conservatively.

Matching identifiers mean the *recorded inputs* match. They do not prove that
an arbitrary Python process, environment, or complete RPG is correct.
"""

from hashlib import sha256
import json
import re


SCHEMA = 'blacklight.mechanics-contract.v1'
_SHA256 = re.compile(r'[0-9a-f]{64}')


def mechanical_sources(sources):
    if not isinstance(sources, dict):
        raise ValueError('Mechanical source manifest must be a mapping')
    selected = {}
    for name, digest in sources.items():
        if not isinstance(name, str):
            raise ValueError('Mechanical source name must be a string')
        portable = name.replace('\\', '/')
        if portable.startswith(('blacklight/', 'combatants/', 'experimental/')) and portable.endswith('.py'):
            if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
                raise ValueError('Mechanical source digest must be SHA-256')
            if portable in selected and selected[portable] != digest:
                raise ValueError('Duplicate normalized mechanical source disagrees')
            selected[portable] = digest
    if not selected:
        raise ValueError('At least one mechanical source is required')
    return selected


def mechanics_digest(ruleset, actions, sources):
    if not isinstance(ruleset, str) or not ruleset.strip() or not isinstance(actions, (list, tuple)):
        raise ValueError('A mechanics contract needs a ruleset and action definitions')
    data = {'schema': SCHEMA, 'ruleset': ruleset, 'actions': actions,
            'sources': mechanical_sources(sources)}
    canonical = json.dumps(data, sort_keys=True, separators=(',', ':'),
                           ensure_ascii=False, allow_nan=False).encode('utf-8')
    return sha256(canonical).hexdigest()


def recorded_contract_status(payload):
    identity = payload.get('mechanics_contract_sha256') if isinstance(payload, dict) else None
    if identity is None:
        return 'not_recorded'
    try:
        expected = mechanics_digest(payload['table_ruleset'], payload['registered_action_modules'],
                                    payload['source_sha256'])
    except (KeyError, TypeError, ValueError):
        return 'invalid'
    return 'recorded_verified' if identity == expected else 'invalid'


def compare_recorded_contracts(first, second):
    """Compare metadata only; missing historical evidence is never called equal."""
    states = [recorded_contract_status(item) for item in (first, second)]
    names = [item.get('table_ruleset') if isinstance(item, dict) else None
             for item in (first, second)]
    changed = []
    try:
        left, right = (mechanical_sources(item['source_sha256']) for item in (first, second))
        changed = sorted(name for name in left.keys() & right.keys() if left[name] != right[name])
    except (KeyError, TypeError, ValueError):
        pass
    if 'invalid' in states:
        outcome = 'invalid_contract'
    elif all(isinstance(name, str) and name for name in names) and names[0] != names[1]:
        outcome = 'different_rulesets'
    elif 'not_recorded' in states:
        outcome = 'unverified_missing_contract'
    elif first['mechanics_contract_sha256'] != second['mechanics_contract_sha256']:
        outcome = 'different_recorded_contracts'
    else:
        outcome = 'matching_recorded_contracts'
    return {'status': outcome, 'contract_status': states,
            'shared_mechanical_sources_changed': changed,
            'limitations': ['Matching recorded contracts do not verify environment, rules or conclusions.',
                            'A changed source requires review; it does not prove which scenarios changed.']}
