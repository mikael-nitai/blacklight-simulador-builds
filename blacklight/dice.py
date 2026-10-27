"""d616 checks. Rule IDs: D616-01/02, EDGE-01/02 in RULES_AUDIT.md."""

from dataclasses import dataclass
from random import Random
from typing import Callable


@dataclass(frozen=True)
class DieRoll:
    left: int
    marvel: int
    right: int

    def __post_init__(self) -> None:
        if any(not 1 <= face <= 6 for face in (self.left, self.marvel, self.right)):
            raise ValueError("Every die face must be between 1 and 6")

    @property
    def fantastic(self) -> bool:
        return self.marvel == 1

    @property
    def ultimate(self) -> bool:
        return self.left == 6 and self.marvel == 1 and self.right == 6

    @property
    def marvel_value(self) -> int:
        return 6 if self.fantastic else self.marvel

    @property
    def total(self) -> int:
        return self.left + self.marvel_value + self.right

    def face(self, index: int) -> int:
        return (self.left, self.marvel, self.right)[index]

    def replace(self, index: int, face: int) -> "DieRoll":
        values = [self.left, self.marvel, self.right]
        values[index] = face
        return DieRoll(*values)


@dataclass(frozen=True)
class Result:
    roll: DieRoll
    total: int
    success: bool
    fantastic: bool
    ultimate: bool


def classify(roll: DieRoll, modifier: int, target: int) -> Result:
    """An ultimate Fantastic succeeds at any *possible* check, regardless of TN."""
    total = roll.total + modifier
    return Result(roll, total, roll.ultimate or total >= target, roll.fantastic, roll.ultimate)


def roll_d616(rng: Random) -> DieRoll:
    return DieRoll(rng.randint(1, 6), rng.randint(1, 6), rng.randint(1, 6))


def _die_quality(index: int, face: int) -> tuple[int, int]:
    # The Marvel logo counts as six and is explicitly the best die for trouble.
    return (6, 1) if index == 1 and face == 1 else (face, 0)


def choose_edge_for_hit(roll: DieRoll, modifier: int, target: int) -> int | None:
    """Choose a die using only visible faces and six possible rerolls.

    Maximize hit probability, then Fantastic-hit probability, then mean total.
    This is a documented policy, not a mechanical rule. Returning None declines
    the edge if no reroll can improve those objectives.
    """
    base = classify(roll, modifier, target)
    base_value = (int(base.success), int(base.success and base.fantastic), base.total)
    best_index: int | None = None
    best_value = tuple(float(x) for x in base_value)
    for index in range(3):
        outcomes = []
        for face in range(1, 7):
            selected = face if _die_quality(index, face) > _die_quality(index, roll.face(index)) else roll.face(index)
            result = classify(roll.replace(index, selected), modifier, target)
            outcomes.append((int(result.success), int(result.success and result.fantastic), result.total))
        value = tuple(sum(row[col] for row in outcomes) / 6 for col in range(3))
        if value > best_value:
            best_index, best_value = index, value
    return best_index


EdgeChooser = Callable[[DieRoll, int, int], int | None]


@dataclass(frozen=True)
class RerollTrace:
    kind: str
    index: int
    original: int
    rolled: int
    kept: int


def resolve_check(
    rng: Random,
    modifier: int,
    target: int,
    *,
    edges: int = 0,
    troubles: int = 0,
    chooser: EdgeChooser = choose_edge_for_hit,
) -> tuple[Result, tuple[RerollTrace, ...]]:
    if edges < 0 or troubles < 0:
        raise ValueError("Edge and trouble counts cannot be negative")
    roll = roll_d616(rng)
    traces: list[RerollTrace] = []
    net = edges - troubles
    if net < 0 and roll.ultimate:
        return classify(roll, modifier, target), ()
    if net > 0:
        for _ in range(net):
            index = chooser(roll, modifier, target)
            if index is None:
                break
            if index not in (0, 1, 2):
                raise ValueError("Edge chooser selected an invalid die")
            original = roll.face(index)
            fresh = rng.randint(1, 6)
            kept = fresh if _die_quality(index, fresh) > _die_quality(index, original) else original
            roll = roll.replace(index, kept)
            traces.append(RerollTrace("edge", index, original, fresh, kept))
    elif net < 0:
        for _ in range(-net):
            if roll.ultimate:
                break
            index = max(range(3), key=lambda i: (_die_quality(i, roll.face(i)), -i))
            original = roll.face(index)
            fresh = rng.randint(1, 6)
            kept = fresh if _die_quality(index, fresh) < _die_quality(index, original) else original
            roll = roll.replace(index, kept)
            traces.append(RerollTrace("trouble", index, original, fresh, kept))
    return classify(roll, modifier, target), tuple(traces)
