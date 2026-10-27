"""Visible-state policies for the fixed-contact three-actor prototype."""

from dataclasses import dataclass

from blacklight.dice import DieRoll, choose_edge_for_hit


@dataclass(frozen=True)
class GroupView:
    actor: int
    names: tuple[str, ...]
    health: tuple[int, ...]
    defenses: tuple[int, ...]
    conscious: tuple[bool, ...]
    shield_active: tuple[bool, ...]
    reactions: tuple[int, ...]
    round: int


@dataclass(frozen=True)
class GroupAction:
    kind: str  # melee, hammer, fast_strikes, wait
    targets: tuple[int, ...] = ()


@dataclass(frozen=True)
class GroupPolicy:
    name: str
    preferred: str = "melee"
    shield_react: bool = False
    shield_end_turn: bool = False
    riposte: bool = True

    def choose_action(self, view: GroupView) -> GroupAction:
        enemies = [i for i, alive in enumerate(view.conscious)
                   if alive and (i == 0) != (view.actor == 0)]
        if not enemies:
            return GroupAction("wait")
        if self.preferred == "fast_strikes":
            return GroupAction("fast_strikes", tuple(enemies[:2]))
        target = min(enemies, key=lambda i: (view.health[i], i))
        return GroupAction(self.preferred, (target,))

    def choose_riposte(self, view: GroupView, source: int) -> GroupAction | None:
        if not self.riposte or view.reactions[view.actor] < 1:
            return None
        return GroupAction("hammer" if self.preferred == "hammer" else "melee",
                           (source,))

    def use_shield_reaction(self, view: GroupView) -> bool:
        return self.shield_react and not view.shield_active[view.actor]

    def use_shield_end_turn(self, view: GroupView) -> bool:
        return self.shield_end_turn and not view.shield_active[view.actor]

    def choose_edge_die(self, roll: DieRoll, modifier: int,
                        target: int, context: str) -> int | None:
        return choose_edge_for_hit(roll, modifier, target)


GROUP_HAMMER = GroupPolicy("group_hammer", preferred="hammer")
GROUP_HAMMER_SHIELD = GroupPolicy("group_hammer_shield", preferred="hammer",
                                  shield_react=True, shield_end_turn=True)
GROUP_FAST = GroupPolicy("group_bare_fast", preferred="fast_strikes")
GROUP_ENEMY = GroupPolicy("group_focus_fire", preferred="melee", riposte=False)
