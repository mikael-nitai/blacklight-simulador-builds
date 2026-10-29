"""Construct an auditable record for the isolated experimental Ram transaction."""

from dataclasses import asdict

from .ram_transaction import execute_ram


def record_ram(state, first, second, **parameters):
    transaction = execute_ram(state, first, second, **parameters)
    return {'schema': 'blacklight-experimental-ram-transaction-v1',
            'first': asdict(first), 'second': asdict(second),
            'before': asdict(transaction.before), 'after': asdict(transaction.after),
            'parameters': {**parameters, 'target_faces': list(parameters['target_faces']),
                           'attacker_faces': (list(parameters['attacker_faces'])
                                              if parameters.get('attacker_faces') is not None else None)},
            'impact': asdict(transaction.impact),
            'scope': 'synthetic simultaneous damage; no Heroic, Shield, Riposte or weapon effects'}


def record_table_ram(state, first, second, *, attacker_faces, **parameters):
    """Record only the independently rolled pools confirmed by the table."""
    if 'self_pool' in parameters:
        raise ValueError('The current table requires separately rolled pools')
    return record_ram(state, first, second, self_pool='separate',
                      attacker_faces=attacker_faces, **parameters)
