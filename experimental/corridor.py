"""One corridor geometry shared by historical and current combat resolvers."""

from dataclasses import replace

from blacklight.engine import IllegalAction, Move, TerrainView
from combatants.battlefields import CorridorMap
from combatants.modular_duel import ModularDuel
from combatants.split_fast import SplitFastDuel


class CorridorGeometry:
    def __init__(self, *args, length: int, initial_positions: tuple[int, int],
                 **kwargs) -> None:
        layout = CorridorMap(length, tuple(initial_positions))
        left, right = layout.initial_positions
        if "initial_distance" in kwargs:
            raise ValueError("Initial distance is derived from positions")
        super().__init__(*args, initial_distance=right - left, **kwargs)
        self.length = length
        self.positions = [left, right]
        self.wall_reached = right == length
        self.contact_occurred = right - left <= 1

    def observe(self, actor: int):
        self._assert_geometry()
        observation = super().observe(actor)
        return replace(observation, terrain=TerrainView(
            'corridor', (self.length + 1, 1), (self.positions[actor], 0),
            (self.positions[1 - actor], 0)))

    def _assert_geometry(self) -> None:
        if (len(self.positions) != 2 or any(type(value) is not int for value in self.positions)
                or type(self.distance) is not int
                or not 0 <= self.positions[0] < self.positions[1] <= self.length
                or self.distance != self.positions[1] - self.positions[0]):
            raise RuntimeError('Corridor positions and distance are inconsistent')

    def _attack_check_spec(self, actor: int, kind: str):
        self._assert_geometry()
        return super()._attack_check_spec(actor, kind)

    def _move(self, actor: int, move: Move, *, as_standard: bool = False) -> None:
        if (type(actor) is not int or actor not in (0, 1)
                or not isinstance(move, Move) or type(move.steps) is not int
                or type(as_standard) is not bool):
            raise IllegalAction('Corridor movement requires an actor and integer grid steps')
        self._assert_geometry()
        fighter = self.fighters[actor]
        if (self.active_actor != actor or not fighter.conscious or
                fighter.stunned_by is not None):
            raise IllegalAction("Movement outside actor's turn")
        if as_standard and not fighter.standard_available:
            raise IllegalAction("Standard action is unavailable")
        if not as_standard and not fighter.movement_available:
            raise IllegalAction("Movement action is unavailable")
        if (move.direction not in ("stay", "approach", "retreat") or
                not 0 <= move.steps <= fighter.profile.run_speed or
                move.direction == "stay" and move.steps != 0):
            raise IllegalAction("Invalid corridor movement")
        if as_standard:
            fighter.standard_available = False
        else:
            fighter.movement_available = False
        before_positions = tuple(self.positions)
        before_distance = self.distance
        x = self.positions[actor]
        if move.direction == "approach":
            self.positions[actor] = (
                min(x + move.steps, self.positions[1] - 1) if actor == 0
                else max(x - move.steps, self.positions[0] + 1))
        elif move.direction == "retreat":
            self.positions[actor] = (
                max(0, x - move.steps) if actor == 0
                else min(self.length, x + move.steps))
        self.distance = self.positions[1] - self.positions[0]
        self.wall_reached |= self.positions[1] == self.length
        self.contact_occurred |= self.distance <= 1
        self._record("movement", ("ACT-01", "ACT-06", "MAP-01"),
                     actor=fighter.profile.name, direction=move.direction,
                     steps=move.steps,
                     actual_steps=abs(self.positions[actor] - x),
                     as_standard=as_standard,
                     positions_before=list(before_positions),
                     positions_after=list(self.positions),
                     corridor_length=self.length,
                     distance_before=before_distance,
                     distance_after=self.distance)

    def _attack(self, actor: int, kind: str, *, reaction: bool = False,
                offhand: str | None = None, **attack_context):
        self._assert_geometry()
        before = self.distance
        result = super()._attack(actor, kind, reaction=reaction,
                                 offhand=offhand, **attack_context)
        if self.distance != before:
            raise NotImplementedError(
                "Knockback in a corridor needs explicit wall/collision rules")
        return result

    def _validate_knockback(self, actor: int, spaces: int) -> None:
        if spaces > 0:
            raise NotImplementedError('Corridor knockback/collision is not modeled; damage was not applied')
        return super()._validate_knockback(actor, spaces)


class CorridorDuel(CorridorGeometry, ModularDuel):
    """Historical single-check Fast contract, retained for reproducibility."""


class SplitFastCorridorDuel(CorridorGeometry, SplitFastDuel):
    """Current two-check Fast contract with exactly the same movement geometry."""
