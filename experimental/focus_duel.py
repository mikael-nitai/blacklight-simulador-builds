"""Fixed-contact two-actor Mental Punch stress test, isolated from `Duel`.

It supports only Victor's Hammer/Shield/Riposte and a synthetic Mental Punch
attacker. No generic telepathy, movement, Karma, or concentration is modeled.
"""

from dataclasses import dataclass
from random import Random

from blacklight.damage import calculate
from blacklight.dice import resolve_check
from blacklight.engine import Fighter, Profile
from .focus_primitives import resolve_mental_punch


STRATEGIES = ("hammer", "shield_reactive", "shield_endturn")


@dataclass(frozen=True)
class FocusDuelResult:
    seed: int
    outcome: str
    rounds: int
    bonus_round_occurred: bool
    final_health: tuple[int, int]
    final_focus: tuple[int, int]
    ever_demoralized: bool
    log: tuple[dict, ...]


class FocusDuel:
    def __init__(self, victor: Profile, mentalist: Profile, *,
                 strategy: str, shield_focus_reduction: int,
                 seed: int, max_rounds: int = 30, audit: bool = False) -> None:
        if (strategy not in STRATEGIES or shield_focus_reduction not in (0, 2)
                or max_rounds < 1):
            raise ValueError("Invalid Focus duel configuration")
        if ("hammer" not in victor.weapons or "shield" not in victor.weapons
                or "riposte" not in victor.powers or
                "mental_punch" not in mentalist.powers or
                victor.name == mentalist.name):
            raise ValueError("Required powers, weapons, or names missing")
        self.fighters = [Fighter(victor), Fighter(mentalist)]
        self.strategy = strategy
        self.shield_focus_reduction = shield_focus_reduction
        self.seed = seed
        self.rng = Random(seed)
        self.max_rounds = max_rounds
        self.audit = audit
        self.log: list[dict] = []
        self.seq = 0
        self.round = 0
        self.bonus_round = False
        self.turn_counts = [0, 0]
        self.trigger = 0
        self.ever_demoralized = False

    def _record(self, event_type: str, rules: tuple[str, ...], **data: object) -> None:
        if self.audit:
            self.seq += 1
            self.log.append({"seq": self.seq, "round": self.round,
                             "bonus_round": self.bonus_round,
                             "type": event_type, "rules": list(rules), **data})

    def _reset_reactions(self) -> None:
        for fighter in self.fighters:
            fighter.reactions = 1 + int("combat_reflexes" in fighter.profile.traits)
            fighter.reacted_to.clear()
            self._record("reaction_reset", ("ACT-03",),
                         actor=fighter.profile.name,
                         reactions=fighter.reactions)

    def _initiative(self) -> tuple[tuple[int, int], tuple[bool, bool]]:
        checks = []
        modifiers = []
        for actor, fighter in enumerate(self.fighters):
            p = fighter.profile
            modifier = (p.initiative_modifier if p.initiative_modifier is not None
                        else p.vigilance)
            check, rerolls = resolve_check(
                self.rng, modifier, 0,
                edges=int("situational_awareness" in p.traits))
            checks.append(check)
            modifiers.append(modifier)
            self._record("initiative", ("ACT-02",), actor=p.name,
                         roll=[check.roll.left, check.roll.marvel, check.roll.right],
                         rerolls=[vars(x) for x in rerolls],
                         total=check.total, fantastic=check.fantastic)
        order = tuple(sorted(range(2), key=lambda i: (-checks[i].total,
                            -int(checks[i].fantastic), -modifiers[i], i)))
        return order, (checks[0].fantastic, checks[1].fantastic)

    def _check(self, actor: int, defense: int, kind: str,
               *, reaction: bool = False) -> tuple[object, int]:
        fighter = self.fighters[actor]
        p = fighter.profile
        edges = int(actor == 0 and "blazing_fast_fists" in p.powers)
        troubles = int(fighter.focus <= 0)
        check, rerolls = resolve_check(self.rng, p.melee, defense,
                                        edges=edges, troubles=troubles)
        self.trigger += 1
        trigger = self.trigger
        self._record("attack_check", ("D616-01", "COND-03"), actor=p.name,
                     target=self.fighters[1 - actor].profile.name,
                     kind=kind, reaction=reaction, trigger=trigger,
                     roll=[check.roll.left, check.roll.marvel, check.roll.right],
                     rerolls=[vars(x) for x in rerolls],
                     edges=edges, troubles=troubles,
                     modifier=p.melee, defense=defense,
                     total=check.total, success=check.success,
                     fantastic=check.fantastic)
        return check, trigger

    def _activate_shield(self, *, trigger: int | None,
                         timing: str) -> None:
        f = self.fighters[0]
        if (f.shield_active or f.reactions < 1 or f.stunned_by is not None
                or f.focus <= -f.profile.max_focus or not f.conscious):
            return
        if trigger is not None and trigger in f.reacted_to:
            return
        f.reactions -= 1
        if trigger is not None:
            f.reacted_to.add(trigger)
        self._record("reaction_spent", ("ACT-03", "HR-04"),
                     actor=f.profile.name, trigger=trigger,
                     remaining=f.reactions)
        f.shield_active = True
        self._record("shield_activate", ("HR-04",), actor=f.profile.name,
                     timing=timing, trigger=trigger)

    def _hammer(self, *, reaction: bool = False) -> None:
        attacker, target = self.fighters
        if attacker.shield_active:
            attacker.shield_active = False
            self._record("shield_deactivate", ("HR-04",),
                         actor=attacker.profile.name, cost="free")
        check, trigger = self._check(0, target.profile.melee_defense,
                                     "hammer", reaction=reaction)
        p = attacker.profile
        bonus = p.melee_bonus + 2 if "mighty" in p.powers else max(p.melee_bonus, 2)
        calculated = (calculate(check.roll.marvel, p.rank, p.melee,
                                (bonus,), target.profile.health_dr,
                                check.fantastic)
                      if check.success else 0)
        before = target.health
        after = before - calculated
        if p.heroic and after <= -target.profile.max_health:
            after = -target.profile.max_health + 1
        target.health = after
        self._record("attack_target", ("DMG-01", "HR-02"), actor=p.name,
                     target=target.profile.name, kind="hammer", trigger=trigger,
                     calculated_damage=calculated, applied=before - after,
                     reduction=target.profile.health_dr,
                     health_before=before, health_after=after)
        if check.success and check.fantastic and target.conscious:
            target.stunned_by = 0
            target.stun_expires_on_actor_turn = self.turn_counts[0] + 1
            self._record("condition_start", ("COND-02", "HR-02"),
                         actor=target.profile.name, condition="stunned",
                         expires_on_actor=p.name)

    def _mental_punch(self) -> None:
        attacker, target = self.fighters[1], self.fighters[0]
        check, trigger = self._check(1, target.profile.melee_defense,
                                     "mental_punch")
        if check.success and self.strategy != "hammer":
            self._activate_shield(trigger=trigger, timing="after_hit")
        before = target.focus
        out = resolve_mental_punch(
            check.roll, attacker_rank=attacker.profile.rank,
            attacker_melee=attacker.profile.melee,
            target_melee_defense=target.profile.melee_defense,
            target_focus=before, target_max_focus=target.profile.max_focus,
            shield_reduction=(self.shield_focus_reduction
                              if target.shield_active else 0),
            attacker_heroic=attacker.profile.heroic)
        target.focus = out.focus_after
        self.ever_demoralized |= out.demoralized
        self._record("attack_target", ("DMG-05", "MENTAL-01"),
                     actor=attacker.profile.name, target=target.profile.name,
                     kind="mental_punch", trigger=trigger,
                     calculated_damage=out.damage, applied=out.applied,
                     reduction=(self.shield_focus_reduction
                                if target.shield_active else 0),
                     focus_before=before, focus_after=out.focus_after,
                     demoralized=out.demoralized, shattered=out.shattered)
        if out.stunned and target.focus > -target.profile.max_focus:
            target.stunned_by = 1
            target.stun_expires_on_actor_turn = self.turn_counts[1] + 1
            self._record("condition_start", ("COND-02", "MENTAL-01"),
                         actor=target.profile.name, condition="stunned",
                         expires_on_actor=attacker.profile.name)
        if not check.success:
            self._riposte(trigger)

    def _riposte(self, trigger: int) -> None:
        victor, enemy = self.fighters
        if (not victor.conscious or victor.focus <= -victor.profile.max_focus
                or victor.stunned_by is not None or victor.reactions < 1
                or trigger in victor.reacted_to or not enemy.conscious):
            return
        victor.reactions -= 1
        victor.reacted_to.add(trigger)
        self._record("reaction_spent", ("ACT-03", "POW-06"),
                     actor=victor.profile.name, trigger=trigger,
                     remaining=victor.reactions)
        self._hammer(reaction=True)

    def _turn(self, actor: int) -> None:
        fighter = self.fighters[actor]
        if not fighter.conscious or fighter.focus <= -fighter.profile.max_focus:
            return
        self.turn_counts[actor] += 1
        other = self.fighters[1 - actor]
        if (other.stunned_by == actor and
                other.stun_expires_on_actor_turn is not None and
                self.turn_counts[actor] >= other.stun_expires_on_actor_turn):
            other.stunned_by = None
            other.stun_expires_on_actor_turn = None
            self._record("condition_end", ("COND-02",),
                         actor=other.profile.name, condition="stunned")
        self._record("turn_start", ("ACT-01",), actor=fighter.profile.name,
                     reactions=fighter.reactions, focus=fighter.focus)
        if fighter.stunned_by is not None:
            self._record("turn_skipped", ("COND-02",),
                         actor=fighter.profile.name, reason="stunned")
        elif actor == 0:
            self._hammer()
        else:
            self._mental_punch()
        if "healing_factor" in fighter.profile.powers:
            before = fighter.health
            fighter.health = min(fighter.profile.max_health,
                                 before + fighter.profile.resilience)
            self._record("heal", ("POW-03",), actor=fighter.profile.name,
                         health_before=before, health_after=fighter.health)
        if actor == 0 and self.strategy == "shield_endturn":
            self._activate_shield(trigger=None, timing="end_turn")
        self._record("turn_end", ("ACT-01",), actor=fighter.profile.name,
                     health=fighter.health, focus=fighter.focus)

    def _outcome(self) -> str | None:
        victor, enemy = self.fighters
        if victor.health <= 0 or victor.focus <= -victor.profile.max_focus:
            return "loss"
        if enemy.health <= 0 or enemy.focus <= -enemy.profile.max_focus:
            return "win"
        return None

    def _finish(self, outcome: str, bonus: bool) -> FocusDuelResult:
        return FocusDuelResult(
            self.seed, outcome, self.round, bonus,
            tuple(f.health for f in self.fighters),
            tuple(f.focus for f in self.fighters),
            self.ever_demoralized, tuple(self.log))

    def run(self) -> FocusDuelResult:
        order, fantastics = self._initiative()
        bonus_order = tuple(i for i in order if fantastics[i])
        if bonus_order:
            self.round = 0
            self.bonus_round = True
            self._reset_reactions()
            for actor in bonus_order:
                self._turn(actor)
                outcome = self._outcome()
                if outcome is not None:
                    return self._finish(outcome, True)
        self.bonus_round = False
        for round_number in range(1, self.max_rounds + 1):
            self.round = round_number
            self._reset_reactions()
            for actor in order:
                self._turn(actor)
                outcome = self._outcome()
                if outcome is not None:
                    return self._finish(outcome, bool(bonus_order))
        return self._finish("inconclusive", bool(bonus_order))
