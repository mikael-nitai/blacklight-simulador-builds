import unittest

from experimental.reaction_pools import ReactionPools, spend_reaction, start_round


class ReactionPoolsTests(unittest.TestCase):
    def test_fast_hands_reaction_is_reserved_for_ranged_weapons_powers(self):
        initial = start_round(combat_reflexes=True, fast_hands=True)
        result = spend_reaction(initial, pool='fast_hands', trigger=1,
                                power_set='ranged_weapons', can_react=True)
        self.assertEqual((result.ordinary, result.fast_hands), (2, 0))
        for power_set in ('none', 'martial_arts', 'shield', 'ordinary_attack'):
            with self.subTest(power_set=power_set), self.assertRaises(ValueError):
                spend_reaction(initial, pool='fast_hands', trigger=1,
                               power_set=power_set, can_react=True)

    def test_ordinary_reactions_can_pay_for_ranged_power(self):
        initial = start_round(combat_reflexes=False, fast_hands=True)
        result = spend_reaction(initial, pool='ordinary', trigger=2,
                                power_set='ranged_weapons', can_react=True)
        self.assertEqual((result.ordinary, result.fast_hands), (0, 1))

    def test_one_character_cannot_use_two_reactions_on_same_trigger(self):
        initial = start_round(combat_reflexes=True, fast_hands=True)
        after = spend_reaction(initial, pool='ordinary', trigger=3,
                               power_set='none', can_react=True)
        with self.assertRaises(ValueError):
            spend_reaction(after, pool='fast_hands', trigger=3,
                           power_set='ranged_weapons', can_react=True)
        new_trigger = spend_reaction(after, pool='fast_hands', trigger=4,
                                     power_set='ranged_weapons', can_react=True)
        self.assertEqual((new_trigger.ordinary, new_trigger.fast_hands), (1, 0))

    def test_reset_replenishes_both_pools_and_triggers(self):
        state = start_round(combat_reflexes=False, fast_hands=True)
        state = spend_reaction(state, pool='fast_hands', trigger=7,
                               power_set='ranged_weapons', can_react=True)
        reset = start_round(combat_reflexes=False, fast_hands=True)
        self.assertEqual(reset, ReactionPools(1, 1))
        self.assertNotEqual(state, reset)

    def test_invalid_state_and_request_are_rejected(self):
        for args in ((True, 1), (1, 2), (-1, 1)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                ReactionPools(*args)
        state = start_round(combat_reflexes=False, fast_hands=True)
        for change in (dict(pool='other'), dict(trigger=True), dict(can_react=1), dict(power_set='')):
            args = dict(pool='ordinary', trigger=1, power_set='none', can_react=True)
            args.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                spend_reaction(state, **args)
        with self.assertRaises(ValueError):
            spend_reaction(state, pool='ordinary', trigger=1, power_set='none', can_react=False)
