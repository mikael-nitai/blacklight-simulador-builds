"""One-cell-wide bounded corridor for the frozen two-actor Duel engine."""

from blacklight.engine import IllegalAction, Move
from combatants.modular_duel import ModularDuel


class CorridorDuel(ModularDuel):
    def __init__(self, *args, length: int, initial_positions: tuple[int, int],
                 **kwargs) -> None:
        left, right = initial_positions
        if not (0 <= left < right <= length):
            raise ValueError("Characters must start in order inside corridor")
        if "initial_distance" in kwargs:
            raise ValueError("Initial distance is derived from positions")
        super().__init__(*args, initial_distance=right - left, **kwargs)
        self.length = length
        self.positions = [left, right]
        self.wall_reached = right == length
        self.contact_occurred = right - left <= 1

    def _move(self, actor: int, move: Move, *, as_standard: bool = False) -> None:
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
                offhand: str | None = None):
        before = self.distance
        result = super()._attack(actor, kind, reaction=reaction,
                                 offhand=offhand)
        if self.distance != before:
            raise NotImplementedError(
                "Knockback in a corridor needs explicit wall/collision rules")
        return result
