"""Contract comparisons distinguish recorded changes from absent evidence."""

from copy import deepcopy
import unittest

from blacklight.mechanics_contract import (compare_recorded_contracts, mechanics_digest,
                                            recorded_contract_status)


def record(*, ruleset='split_fast_v3', healing=2, fast='a', reaction='b'):
    value = {'table_ruleset': ruleset,
             'registered_action_modules': [{'kind': 'heal', 'health_per_focus': healing}],
             'source_sha256': {'combatants/split_fast.py': fast * 64,
                               'blacklight/engine.py': reaction * 64}}
    value['mechanics_contract_sha256'] = mechanics_digest(
        value['table_ruleset'], value['registered_action_modules'], value['source_sha256'])
    return value


class TestMechanicsContract(unittest.TestCase):
    def test_three_distinct_mechanical_changes_do_not_match_the_recorded_contract(self):
        base = record()
        for variant in (record(healing=3), record(fast='c'), record(reaction='d')):
            with self.subTest(variant=variant):
                comparison = compare_recorded_contracts(base, variant)
                self.assertEqual(comparison['status'], 'different_recorded_contracts')
                self.assertNotEqual(base['mechanics_contract_sha256'],
                                    variant['mechanics_contract_sha256'])
        self.assertEqual(compare_recorded_contracts(base, deepcopy(base))['status'],
                         'matching_recorded_contracts')

    def test_history_without_contract_is_unknown_even_if_sources_match(self):
        current = record()
        old = deepcopy(current)
        old.pop('mechanics_contract_sha256')
        self.assertEqual(compare_recorded_contracts(old, current)['status'],
                         'unverified_missing_contract')
        old['source_sha256']['blacklight/engine.py'] = 'c' * 64
        self.assertEqual(compare_recorded_contracts(old, current)['shared_mechanical_sources_changed'],
                         ['blacklight/engine.py'])

    def test_altered_metadata_and_unknown_rule_versions_are_not_conflated(self):
        base, changed = record(), record()
        changed['registered_action_modules'][0]['health_per_focus'] = 99
        self.assertEqual(recorded_contract_status(changed), 'invalid')
        self.assertEqual(compare_recorded_contracts(base, changed)['status'], 'invalid_contract')
        other = record(ruleset='literal_marvel_pool_v2')
        self.assertEqual(compare_recorded_contracts(base, other)['status'], 'different_rulesets')

    def test_windows_paths_and_json_round_trip_do_not_change_identity(self):
        import json
        base = record()
        renamed = deepcopy(base)
        renamed['source_sha256'] = {key.replace('/', '\\'): value
                                    for key, value in renamed['source_sha256'].items()}
        renamed = json.loads(json.dumps(renamed))
        self.assertEqual(recorded_contract_status(renamed), 'recorded_verified')
        self.assertEqual(compare_recorded_contracts(base, renamed)['status'], 'matching_recorded_contracts')


if __name__ == '__main__':
    unittest.main()
