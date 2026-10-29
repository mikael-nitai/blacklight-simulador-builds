"""Detect Ram opportunities in the existing 1D duel; never resolve the attack."""

from combatants.split_fast import SplitFastDuel
from .ram_trigger import Approach, ram_triggered


class RamOpportunityDuel(SplitFastDuel):
    """Experimental observer: produces markers without changing combat decisions."""

    execution_scope = 'experimental_ram_opportunity_only'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ram_approaches = {}

    def _turn(self, actor):
        self._ram_approaches.pop(actor, None)
        try:
            return super()._turn(actor)
        finally:
            self._ram_approaches.pop(actor, None)

    def _move(self, actor, move, *, as_standard=False):
        before = self.distance
        super()._move(actor, move, as_standard=as_standard)
        after = self.distance
        fighter = self.fighters[actor]
        target = self.fighters[self._target_index(actor)]
        actual = before - after
        if move.direction != 'approach' or actual <= 0:
            self._ram_approaches.pop(actor, None)
            return
        segment = Approach(fighter.profile.name, target.profile.name,
                           self.turn_counts[actor], 'standard' if as_standard else 'movement',
                           before, after, fighter.profile.run_speed)
        if not as_standard:
            self._ram_approaches[actor] = segment
            return
        first = self._ram_approaches.pop(actor, None)
        if (first is not None and target.conscious
                and ram_triggered(first, segment, reaction_available=fighter.reactions > 0,
                                  able_to_act=fighter.conscious and fighter.stunned_by is None)):
            self._record('ram_opportunity', ('ACT-01', 'ACT-03'), actor=fighter.profile.name,
                         target=target.profile.name, first_before=first.before,
                         first_after=first.after, second_after=segment.after,
                         speed=segment.speed, reactions=fighter.reactions,
                         scope='opportunity only; no reaction or attack performed')
