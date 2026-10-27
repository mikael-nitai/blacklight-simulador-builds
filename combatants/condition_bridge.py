"""Shared start-turn condition bridge for the existing combat prototypes.

The immutable planner accepts any roster size. Each caller explicitly chooses
its supported conditions and subjects; it does not gain new powers by importing
the bridge. Existing fighter flags remain the authoritative mutable state.
"""

from dataclasses import dataclass
from typing import Callable, Protocol, Sequence

from .lifecycle import Boundary, ExpirationPlan, TimePoint, TimedEffect, expiration_plan


@dataclass(frozen=True)
class ConditionTiming:
    dodging: bool
    stunned_by: int | None
    stun_deadline: int | None

    def __post_init__(self) -> None:
        if (type(self.dodging) is not bool
                or self.stunned_by is not None and
                (type(self.stunned_by) is not int or self.stunned_by < 0)
                or self.stun_deadline is not None and
                (type(self.stun_deadline) is not int or self.stun_deadline < 1)):
            raise ValueError('Invalid condition timing snapshot')


def turn_start_plan(states: tuple[ConditionTiming, ...], counts: tuple[int, ...],
                    actor: int, *, include_dodge: bool = True,
                    stun_subjects: tuple[int, ...] | None = None) -> ExpirationPlan:
    """Plan expirations after the caller has advanced this actor's turn count."""
    if (not isinstance(states, tuple) or not states
            or any(not isinstance(state, ConditionTiming) for state in states)
            or not isinstance(counts, tuple) or len(counts) != len(states)
            or any(type(count) is not int or count < 0 for count in counts)
            or type(actor) is not int or not 0 <= actor < len(states)
            or counts[actor] < 1 or type(include_dodge) is not bool
            or any(state.stunned_by is not None and state.stunned_by >= len(states)
                   for state in states)):
        raise ValueError('Invalid roster or clock for condition expiration')
    subjects = tuple(range(len(states))) if stun_subjects is None else stun_subjects
    if (not isinstance(subjects, tuple)
            or any(type(index) is not int or not 0 <= index < len(states) for index in subjects)
            or len(set(subjects)) != len(subjects)):
        raise ValueError('Condition subjects must be distinct roster indices')
    now = TimePoint(Boundary.TURN_START, counts[actor], actor)
    effects = []
    if include_dodge and states[actor].dodging:
        effects.append(TimedEffect(f'dodge:{actor}', 'dodge', actor, actor,
                                   (now,), ('ACT-07',)))
    for subject in subjects:
        state = states[subject]
        if state.stunned_by is None:
            continue
        deadlines = (() if state.stun_deadline is None else
                     (TimePoint(Boundary.TURN_START, state.stun_deadline, state.stunned_by),))
        effects.append(TimedEffect(f'stunned:{subject}', 'stunned', subject,
                                   state.stunned_by, deadlines, ('COND-02',)))
    return expiration_plan(tuple(effects), now)


class NamedProfile(Protocol):
    name: str


class FighterTiming(Protocol):
    dodging: bool
    stunned_by: int | None
    stun_expires_on_actor_turn: int | None
    profile: NamedProfile


def expire_at_turn_start(fighters: Sequence[FighterTiming], counts: Sequence[int],
                         actor: int, record: Callable[..., None], *,
                         include_dodge: bool = True,
                         stun_subjects: tuple[int, ...] | None = None) -> ExpirationPlan:
    """Validate the whole snapshot before clearing any fighter flag or logging."""
    if not callable(record):
        raise ValueError('Condition expiration requires an engine event recorder')
    fighters = tuple(fighters)
    names = tuple(fighter.profile.name for fighter in fighters)
    if (any(not isinstance(name, str) or not name.strip() for name in names)
            or len(set(names)) != len(names)):
        raise ValueError('Condition expiration requires distinct named combatants')
    states = tuple(ConditionTiming(fighter.dodging, fighter.stunned_by,
                                   fighter.stun_expires_on_actor_turn)
                   for fighter in fighters)
    plan = turn_start_plan(states, tuple(counts), actor,
                           include_dodge=include_dodge, stun_subjects=stun_subjects)
    for effect in plan.expired:
        fighter = fighters[effect.subject]
        if effect.kind == 'dodge':
            fighter.dodging = False
            record('dodge_end', effect.rules, actor=names[effect.subject])
        else:
            fighter.stunned_by = None
            fighter.stun_expires_on_actor_turn = None
            record('condition_end', effect.rules,
                   actor=names[effect.subject], condition='stunned')
    return plan
