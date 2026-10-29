from copy import deepcopy
from itertools import product
import unittest

from experimental.ram_record import record_ram, record_table_ram
from experimental.ram_record_audit import audit_ram_record, audit_table_ram_record
from experimental.ram_transaction import RamState
from experimental.ram_trigger import Approach


class IndependentRamAuditTests(unittest.TestCase):
    def setUp(self):
        self.state = RamState(20, 100, 2, True, False)
        self.first = Approach('Victor', 'Alvo', 3, 'movement', 10, 5, 5)
        self.second = Approach('Victor', 'Alvo', 3, 'standard', 5, 1, 5)
        self.args = dict(success=True, fantastic_success=True, full_dice=2, ability=3,
                         target_reduction=0, attacker_reduction=1,
                         target_faces=(1, 4), self_pool='shared')

    def test_records_pass_independent_enumeration(self):
        for faces in product(range(1, 7), repeat=2):
            for fantastic in (False, True):
                for mode in ('shared', 'separate'):
                    args = {**self.args, 'target_faces': faces, 'fantastic_success': fantastic,
                            'self_pool': mode}
                    if mode == 'separate':
                        args['attacker_faces'] = tuple(reversed(faces))
                    with self.subTest(faces=faces, fantastic=fantastic, mode=mode):
                        self.assertEqual(audit_ram_record(record_ram(self.state, self.first, self.second, **args)), [])
        miss = {**self.args, 'success': False, 'fantastic_success': False, 'target_faces': ()}
        self.assertEqual(audit_ram_record(record_ram(self.state, self.first, self.second, **miss)), [])

    def test_falsified_records_are_rejected(self):
        original = record_ram(self.state, self.first, self.second, **self.args)
        changes = [
            ('first', 'before', 9), ('second', 'action', 'movement'),
            ('before', 'reactions', 0), ('after', 'reactions', 2),
            ('after', 'attacker_health', 20), ('after', 'target_prone', False),
            ('after', 'attacker_able', 1), ('impact', 'target_damage', 999),
            ('impact', 'attacker_regular', 1.0), ('parameters', 'target_faces', [7, 4]),
            ('parameters', 'self_pool', 'separate'),
        ]
        for section, key, value in changes:
            with self.subTest(section=section, key=key):
                changed = deepcopy(original)
                changed[section][key] = value
                self.assertTrue(audit_ram_record(changed))

    def test_malformed_record_is_rejected(self):
        for record in (None, {}, {'schema': 'blacklight-experimental-ram-transaction-v1'}):
            with self.subTest(record=record):
                self.assertTrue(audit_ram_record(record))

    def test_table_audit_rejects_historical_shared_roll(self):
        shared = record_ram(self.state, self.first, self.second, **self.args)
        self.assertEqual(audit_ram_record(shared), [])
        self.assertTrue(audit_table_ram_record(shared))
        params = {key: value for key, value in self.args.items() if key != 'self_pool'}
        table = record_table_ram(self.state, self.first, self.second,
                                 attacker_faces=(6, 3), **params)
        self.assertEqual(audit_table_ram_record(table), [])
        with self.assertRaises(ValueError):
            record_table_ram(self.state, self.first, self.second,
                             attacker_faces=(6, 3), **self.args)
