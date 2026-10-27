"""Explicit policies that can only request actions from the duel engine."""

from dataclasses import dataclass

from .dice import DieRoll, choose_edge_for_hit
from .engine import Action, Move, Observation


@dataclass(frozen=True)
class RulePolicy:
    """Simple auditable policy, with no access to future dice or engine state.

    Parameters make strategy names operational: `open_stance` spends the first
    available standard action on Attack Stance; `heal_missing` triggers healing
    when at least that much Health is missing; `prefer_fast` selects the
    conservative single-target Fast Strikes variant; `kite` retreats on an
    open field while keeping a ranged target inside normal range.
    """

    name: str
    open_stance: bool = False
    heal_missing: int | None = None
    heal_spend: int = 15
    prefer_fast: bool = False
    weapon: str = "bare"
    offhand: str | None = None
    kite: bool = False
    riposte: bool = True
    move_after_attack: bool = False
    knockback_stance: bool = True
    edge_mode: str = "hit"  # hit, marvel, decline
    always_wait: bool = False
    dodge_below_health: int | None = None
    treat_bleeding: bool = False
    shield_react: bool = False
    shield_standard: bool = False
    shield_end_turn: bool = False

    def choose_move(self, observation: Observation) -> Move | None:
        if self.move_after_attack:
            return None
        return self._desired_move(observation)

    def choose_post_move(self, observation: Observation) -> Move:
        return self._desired_move(observation) if self.move_after_attack else Move()

    def _desired_move(self, observation: Observation) -> Move:
        me, foe, distance = observation.me, observation.foe, observation.distance
        if self.kite and me.ranged_range and foe.ranged_range == 0:
            if distance <= me.ranged_range:
                return Move("retreat", me.run_speed)
            if distance > 2 * me.ranged_range:
                return Move("approach", min(me.run_speed, distance - me.ranged_range))
            return Move()
        desired = me.ranged_range if me.ranged_range else 1
        if distance > desired:
            return Move("approach", min(me.run_speed, distance - desired))
        return Move()

    def choose_action(self, observation: Observation) -> Action:
        me, foe, distance = observation.me, observation.foe, observation.distance
        if self.always_wait:
            return Action("wait")
        if self.shield_standard and not me.shield_active:
            return Action("shield")
        if (self.kite and me.ranged_range and foe.ranged_range == 0
                and distance <= 1 and foe.run_speed >= me.run_speed):
            # Shooting then moving once lets an equally fast pursuer attack
            # next turn. Spend the standard action on a second retreat.
            return Action("move", move=Move("retreat", me.run_speed))
        if self.treat_bleeding and me.bleeding and "healing_factor" not in me.powers:
            return Action("treat_bleeding")
        if self.dodge_below_health is not None and me.health <= self.dodge_below_health:
            return Action("dodge")
        missing = me.max_health - me.health
        if (self.heal_missing is not None and missing >= self.heal_missing
                and "do_this_all_day" in me.powers):
            spend = min(self.heal_spend, 5 * me.rank, me.focus - 1)
            if spend >= 5:
                return Action("heal", spend)
        if self.open_stance and not me.stance and "attack_stance" in me.powers:
            return Action("stance")
        if me.ranged_range and distance <= 2 * me.ranged_range:
            return Action("ranged")
        if distance <= 1:
            if self.weapon == "blade":
                return Action("blade_fast" if self.prefer_fast else "blade",
                              offhand=self.offhand if self.prefer_fast else None)
            if self.weapon == "claw":
                return Action("claw_fast" if self.prefer_fast else "claw",
                              offhand=self.offhand if self.prefer_fast else None)
            if self.weapon == "hammer":
                return Action("hammer_fast" if self.prefer_fast else "hammer",
                              offhand=self.offhand if self.prefer_fast else None)
            if self.prefer_fast and "fast_strikes" in me.powers:
                return Action("fast_strikes")
            return Action("melee")
        if distance > 1 and me.run_speed:
            return Action("move", move=Move("approach", min(me.run_speed, distance - 1)))
        return Action("wait")

    def use_riposte(self, observation: Observation) -> bool:
        return self.riposte and observation.me.reactions > 0

    def choose_riposte_attack(self, observation: Observation) -> Action:
        return Action(self.weapon if self.weapon in {"blade", "claw", "hammer"}
                      else "melee")

    def choose_blade_bonus(self, observation: Observation) -> Action:
        if self.prefer_fast:
            if self.weapon in ("blade", "claw", "hammer") and (self.weapon == "blade" or self.offhand == "blade"):
                return Action(f"{self.weapon}_fast", offhand=self.offhand)
            return Action("blade_fast")
        return Action("blade")

    def choose_edge_die(self, roll: DieRoll, modifier: int,
                        target: int, context: str) -> int | None:
        if self.edge_mode == "decline":
            return None
        if self.edge_mode == "marvel":
            return 1
        return choose_edge_for_hit(roll, modifier, target)

    def choose_knockback(self, observation: Observation, mode: str) -> bool:
        return self.knockback_stance and observation.foe.stance

    def use_shield_reaction(self, observation: Observation,
                            incoming_kind: str) -> bool:
        return self.shield_react and not observation.me.shield_active

    def use_shield_end_turn(self, observation: Observation) -> bool:
        return self.shield_end_turn and not observation.me.shield_active


ATTACK = RulePolicy("attack")
STANCE = RulePolicy("stance_then_attack", open_stance=True)
HEAL = RulePolicy("attack_heal_30_missing", heal_missing=30)
HYBRID = RulePolicy("stance_heal_30_missing", open_stance=True, heal_missing=30)
FAST = RulePolicy("single_target_fast_strikes", prefer_fast=True)
CLAW = RulePolicy("claw_attack", weapon="claw")
BLADE = RulePolicy("blade_attack", weapon="blade")
BLADE_FAST = RulePolicy("blade_fast_strikes", weapon="blade", prefer_fast=True)
HAMMER = RulePolicy("hammer_attack", weapon="hammer")
HAMMER_FAST = RulePolicy("hammer_fast_strikes", weapon="hammer", prefer_fast=True)
BLADE_HAMMER_FAST = RulePolicy("blade_hammer_fast", weapon="blade", offhand="hammer", prefer_fast=True)
CLAW_HAMMER_FAST = RulePolicy("claw_hammer_fast", weapon="claw", offhand="hammer", prefer_fast=True)
SHIELD_BLADE_HAMMER_REACTIVE = RulePolicy(
    "shield_blade_hammer_reactive", weapon="blade", offhand="hammer",
    prefer_fast=True, shield_react=True)
SHIELD_HAMMER_REACTIVE = RulePolicy("shield_hammer_reactive", weapon="hammer",
                                    shield_react=True)
SHIELD_BLADE_REACTIVE = RulePolicy("shield_blade_reactive", weapon="blade",
                                   prefer_fast=True, shield_react=True)
SHIELD_HAMMER_ENDTURN = RulePolicy("shield_hammer_endturn", weapon="hammer",
                                   shield_react=True, shield_end_turn=True)
KITER = RulePolicy("ranged_kiter", kite=True, move_after_attack=True,
                   treat_bleeding=True)
