"""Three-actor fixed-contact prototype, isolated from frozen duel results.

All three actors remain within reach. The module rejects multiple shield or
Riposte users because simultaneous same-trigger priority is not implemented.
It does not resolve biological weapons in multi-target Fast Strikes.
"""

from collections import deque
from dataclasses import dataclass
from random import Random

from blacklight.dice import classify, resolve_check
from blacklight.engine import Fighter, Profile
from blacklight.pool_damage import roll_damage_pool
from combatants.condition_bridge import expire_at_turn_start
from .group_policies import GroupAction, GroupPolicy, GroupView
from .multi_target import Target, resolve_fast_strikes


class IllegalGroupAction(ValueError):
    pass


@dataclass(frozen=True)
class GroupResult:
    seed: int
    outcome: str  # win, loss, inconclusive
    rounds: int
    bonus_round_occurred: bool
    final_health: tuple[int, int, int]
    final_focus: tuple[int, int, int]
    log: tuple[dict, ...]


class GroupBattle:
    def __init__(self, profiles: tuple[Profile, Profile, Profile],
                 policies: tuple[GroupPolicy, GroupPolicy, GroupPolicy],
                 *, seed: int, max_rounds: int = 30, audit: bool = False,
                 fast_zero_dice_bonus: bool = False) -> None:
        if len(profiles) != 3 or len(policies) != 3 or max_rounds < 1:
            raise ValueError("Three profiles/policies and positive horizon required")
        if len({p.name for p in profiles}) != 3:
            raise ValueError("Actor names must be distinct")
        if sum("shield" in p.weapons for p in profiles) > 1:
            raise NotImplementedError("simultaneous shield reactions need priority rules")
        if sum("riposte" in p.powers for p in profiles) > 1:
            raise NotImplementedError("simultaneous Riposte reactions need priority rules")
        self.fighters = [Fighter(p) for p in profiles]
        self.policies = policies
        self.seed = seed
        self.rng = Random(seed)
        self.damage_rng = Random(seed ^ 0xD6162026)
        self.max_rounds = max_rounds
        self.audit = audit
        if type(fast_zero_dice_bonus) is not bool:
            raise ValueError('Damage convention must be explicit boolean')
        self.fast_zero_dice_bonus = fast_zero_dice_bonus
        self.log: list[dict] = []
        self.seq = 0
        self.round = 0
        self.bonus_round = False
        self.turn_counts = [0, 0, 0]
        self.active_actor: int | None = None
        self.trigger_seq = 0
        self.pending: deque[tuple[int, int, int]] = deque()

    def _record(self, kind: str, rules: tuple[str, ...], **data: object) -> None:
        if self.audit:
            self.seq += 1
            self.log.append({"seq": self.seq, "round": self.round,
                             "bonus_round": self.bonus_round, "type": kind,
                             "rules": list(rules), **data})

    def view(self, actor: int) -> GroupView:
        return GroupView(
            actor,
            tuple(f.profile.name for f in self.fighters),
            tuple(f.health for f in self.fighters),
            tuple(f.profile.melee_defense for f in self.fighters),
            tuple(f.conscious for f in self.fighters),
            tuple(f.shield_active for f in self.fighters),
            tuple(f.reactions for f in self.fighters),
            self.round,
        )

    def legal_actions(self, actor: int) -> tuple[GroupAction, ...]:
        f = self.fighters[actor]
        if (actor != self.active_actor or not f.conscious
                or f.stunned_by is not None or not f.standard_available):
            return ()
        enemy_indices = tuple(i for i, other in enumerate(self.fighters)
                              if other.conscious and (i == 0) != (actor == 0))
        actions = [GroupAction("wait")]
        for target in enemy_indices:
            actions.append(GroupAction("melee", (target,)))
            if "hammer" in f.profile.weapons:
                actions.append(GroupAction("hammer", (target,)))
            if "fast_strikes" in f.profile.powers:
                actions.append(GroupAction("fast_strikes", (target,)))
        if "fast_strikes" in f.profile.powers and len(enemy_indices) == 2:
            actions.append(GroupAction("fast_strikes", enemy_indices))
        return tuple(actions)

    def _reset_reactions(self) -> None:
        for f in self.fighters:
            f.reactions = 1 + int("combat_reflexes" in f.profile.traits)
            f.reacted_to.clear()
            self._record("reaction_reset", ("ACT-03", "ACT-04"),
                         actor=f.profile.name, reactions=f.reactions)

    def _activate_shield_after_hit(self, defender: int, trigger: int) -> None:
        f = self.fighters[defender]
        if (not f.conscious or f.stunned_by is not None or f.shield_active
                or f.reactions < 1 or "shield" not in f.profile.weapons
                or trigger in f.reacted_to
                or not self.policies[defender].use_shield_reaction(
                    self.view(defender))):
            return
        f.reactions -= 1
        f.reacted_to.add(trigger)
        f.shield_active = True
        self._record("reaction_spent", ("ACT-03", "HR-04"),
                     actor=f.profile.name, trigger=trigger,
                     remaining=f.reactions)
        self._record("shield_activate", ("HR-04",), actor=f.profile.name,
                     cost="reaction", trigger=trigger, after_hit=True)

    def _attack(self, actor: int, action: GroupAction,
                *, reaction: bool = False) -> None:
        f = self.fighters[actor]
        p = f.profile
        if not f.conscious or f.stunned_by is not None:
            raise IllegalGroupAction("Incapacitated actor cannot attack")
        if action.kind not in ("melee", "hammer", "fast_strikes"):
            raise IllegalGroupAction("Unknown attack")
        if (action.kind == "hammer" and "hammer" not in p.weapons
                or action.kind == "fast_strikes" and "fast_strikes" not in p.powers):
            raise IllegalGroupAction("Actor lacks selected weapon/power")
        if not 1 <= len(action.targets) <= (2 if action.kind == "fast_strikes" else 1):
            raise IllegalGroupAction("Wrong number of targets")
        if len(set(action.targets)) != len(action.targets):
            raise IllegalGroupAction("Fast Strikes targets must be distinct")
        for target in action.targets:
            if (target not in range(3) or not self.fighters[target].conscious
                    or (target == 0) == (actor == 0)):
                raise IllegalGroupAction("Target is not a conscious enemy")
        if f.shield_active:
            f.shield_active = False
            self._record("shield_deactivate", ("HR-04",), actor=p.name,
                         cost="free", reason="attack")
        target_number = max(self.fighters[t].profile.melee_defense
                            for t in action.targets)
        edges = int("blazing_fast_fists" in p.powers)
        if action.kind == "fast_strikes" and "signature_fast_strikes" in p.traits:
            edges += 1
        stunned_targets = [self.fighters[t].stunned_by is not None
                           for t in action.targets]
        if len(set(stunned_targets)) > 1:
            raise NotImplementedError(
                "shared Fast Strikes roll against mixed stunned targets needs adjudication")
        if stunned_targets[0]:
            edges += 1
        check, rerolls = resolve_check(
            self.rng, p.melee, target_number, edges=edges,
            chooser=lambda roll, mod, tn: self.policies[actor].choose_edge_die(
                roll, mod, tn, action.kind))
        self.trigger_seq += 1
        trigger = self.trigger_seq
        target_checks = [(t, classify(check.roll, p.melee,
                                      self.fighters[t].profile.melee_defense))
                         for t in action.targets]
        for target, individual in target_checks:
            if individual.success:
                self._activate_shield_after_hit(target, trigger)
        reductions = {
            t: self.fighters[t].profile.health_dr
            + (2 if self.fighters[t].shield_active else 0)
            for t in action.targets}
        bonuses = ((p.melee_bonus + 2,) if action.kind == "hammer"
                   and "mighty" in p.powers else
                   (p.melee_bonus, 2) if action.kind == "hammer" else
                   (p.melee_bonus,))
        if action.kind == "fast_strikes":
            prepared = tuple(Target(self.fighters[t].profile.name,
                                    self.fighters[t].profile.melee_defense,
                                    self.fighters[t].health, reductions[t])
                             for t in action.targets)
            multi = resolve_fast_strikes(check.roll, self.damage_rng,
                                         melee_modifier=p.melee,
                                         rank=p.rank, damage_ability=p.melee,
                                         bonus_candidates=bonuses,
                                         targets=prepared,
                                         fast_zero_dice_bonus=self.fast_zero_dice_bonus)
            damages = {t: result.damage for t, result in zip(action.targets, multi)}
            faces_by_target = {t: [list(faces) for faces in result.damage_faces]
                               for t, result in zip(action.targets, multi)}
        else:
            damages = {}
            faces_by_target = {}
            for t, individual in target_checks:
                pool = (roll_damage_pool(
                    self.damage_rng,
                    full_multiplier=p.rank + max(0, *bonuses),
                    ability=p.melee, reduction=reductions[t],
                    fantastic=individual.fantastic)
                    if individual.success else None)
                damages[t] = pool.damage if pool is not None else 0
                faces_by_target[t] = [list(pool.faces)] if pool is not None else []
        self._record("attack_check", ("D616-01", "POW-05" if action.kind == "fast_strikes" else "ACT-05"),
                     actor=p.name, mode=action.kind, reaction=reaction,
                     trigger=trigger, targets=[self.fighters[t].profile.name
                                               for t in action.targets],
                     roll=[check.roll.left, check.roll.marvel, check.roll.right],
                     rerolls=[vars(x) for x in rerolls], edges=edges,
                     total=check.total, check_modifier=p.melee)
        for target, individual in target_checks:
            victim = self.fighters[target]
            before = victim.health
            victim.health -= damages[target]
            if p.heroic and victim.health <= -victim.profile.max_health:
                victim.health = -victim.profile.max_health + 1
            applied = before - victim.health
            f.damage_dealt += applied
            victim.damage_taken += applied
            self._record("attack_target", ("DMG-01", "DMG-03"),
                         actor=p.name, target=victim.profile.name,
                         trigger=trigger, mode=action.kind,
                         success=individual.success,
                         fantastic=individual.fantastic,
                         defense=victim.profile.melee_defense,
                         reduction=reductions[target],
                         damage_faces=faces_by_target[target],
                         calculated_damage=damages[target],
                         damage=applied, health_before=before,
                         health_after=victim.health,
                         **({'fast_zero_dice_bonus': True} if self.fast_zero_dice_bonus else {}))
            if (action.kind == "hammer" and individual.success
                    and individual.fantastic and victim.conscious):
                victim.stunned_by = actor
                victim.stun_expires_on_actor_turn = self.turn_counts[actor] + 1
                self._record("condition_start", ("HR-02", "COND-02"),
                             actor=victim.profile.name, condition="stunned",
                             expires_on_actor=p.name)
            if not individual.success:
                self.pending.append((target, actor, trigger))
                self._record("reaction_queued", ("ACT-03", "POW-06"),
                             actor=victim.profile.name, source=p.name,
                             trigger=trigger)

    def _drain_reactions(self) -> None:
        processed = 0
        while self.pending:
            processed += 1
            if processed > 16:
                raise RuntimeError("Group reaction queue exceeded safety bound")
            defender, source, trigger = self.pending.popleft()
            f = self.fighters[defender]
            if (not f.conscious or f.stunned_by is not None or f.reactions < 1
                    or "riposte" not in f.profile.powers
                    or trigger in f.reacted_to
                    or not self.fighters[source].conscious):
                continue
            chosen = self.policies[defender].choose_riposte(self.view(defender), source)
            if chosen is None:
                continue
            if (chosen.kind not in ("melee", "hammer")
                    or chosen.targets != (source,)
                    or chosen.kind == "hammer" and "hammer" not in f.profile.weapons):
                raise IllegalGroupAction("Riposte action invalid")
            f.reactions -= 1
            f.reacted_to.add(trigger)
            self._record("reaction_spent", ("ACT-03", "POW-06"),
                         actor=f.profile.name, trigger=trigger,
                         remaining=f.reactions)
            self._attack(defender, chosen, reaction=True)

    def _turn(self, actor: int) -> None:
        f = self.fighters[actor]
        if not f.conscious:
            return
        if self.active_actor is not None:
            raise RuntimeError("Nested group turn")
        self.active_actor = actor
        self.turn_counts[actor] += 1
        expire_at_turn_start(self.fighters, self.turn_counts, actor, self._record,
                              include_dodge=False)
        f.standard_available = True
        self._record("turn_start", ("ACT-01",), actor=f.profile.name,
                     reactions=f.reactions)
        try:
            if f.stunned_by is not None:
                self._record("turn_skipped", ("COND-02",), actor=f.profile.name,
                             reason="stunned")
            else:
                action = self.policies[actor].choose_action(self.view(actor))
                if action not in self.legal_actions(actor):
                    raise IllegalGroupAction(f"Illegal group action: {action}")
                f.standard_available = False
                if action.kind == "wait":
                    self._record("wait", ("ACT-01",), actor=f.profile.name)
                else:
                    self._attack(actor, action)
                    self._drain_reactions()
            if "healing_factor" in f.profile.powers:
                before = f.health
                f.health = min(f.profile.max_health,
                               f.health + f.profile.resilience)
                self._record("heal", ("POW-03",), actor=f.profile.name,
                             health_before=before, health_after=f.health,
                             effective=f.health - before)
            if (f.conscious and f.stunned_by is None and not f.shield_active
                    and f.reactions > 0 and "shield" in f.profile.weapons
                    and self.policies[actor].use_shield_end_turn(self.view(actor))):
                f.reactions -= 1
                f.shield_active = True
                self._record("reaction_spent", ("ACT-03", "HR-04"),
                             actor=f.profile.name, source="end_turn",
                             remaining=f.reactions)
                self._record("shield_activate", ("HR-04",),
                             actor=f.profile.name, cost="reaction",
                             timing="end_turn")
            self._record("turn_end", ("ACT-01",), actor=f.profile.name,
                         health=f.health, focus=f.focus)
        finally:
            f.standard_available = False
            self.active_actor = None

    def _initiative(self) -> tuple[tuple[int, ...], tuple[bool, ...]]:
        results = []
        modifiers = []
        for actor, f in enumerate(self.fighters):
            modifier = (f.profile.initiative_modifier
                        if f.profile.initiative_modifier is not None
                        else f.profile.vigilance)
            edges = int("situational_awareness" in f.profile.traits)
            check, rerolls = resolve_check(
                self.rng, modifier, 0, edges=edges,
                chooser=lambda roll, mod, tn: self.policies[actor].choose_edge_die(
                    roll, mod, tn, "initiative"))
            results.append(check)
            modifiers.append(modifier)
            self._record("initiative", ("ACT-02",), actor=f.profile.name,
                         total=check.total, fantastic=check.fantastic,
                         roll=[check.roll.left, check.roll.marvel, check.roll.right],
                         rerolls=[vars(x) for x in rerolls])
        order = tuple(sorted(range(3), key=lambda i: (-results[i].total,
                           -int(results[i].fantastic), -modifiers[i], i)))
        return order, tuple(result.fantastic for result in results)

    def _outcome(self) -> str | None:
        if not self.fighters[0].conscious:
            return "loss"
        if not any(f.conscious for f in self.fighters[1:]):
            return "win"
        return None

    def _finish(self, outcome: str, bonus: bool) -> GroupResult:
        return GroupResult(self.seed, outcome, self.round, bonus,
                           tuple(f.health for f in self.fighters),
                           tuple(f.focus for f in self.fighters),
                           tuple(self.log))

    def run(self) -> GroupResult:
        order, fantastics = self._initiative()
        bonus_order = tuple(i for i in order if fantastics[i])
        if bonus_order:
            self.round = 0
            self.bonus_round = True
            self._reset_reactions()
            for actor in bonus_order:
                self._turn(actor)
                outcome = self._outcome()
                if outcome:
                    return self._finish(outcome, True)
        self.bonus_round = False
        for round_number in range(1, self.max_rounds + 1):
            self.round = round_number
            self._reset_reactions()
            for actor in order:
                self._turn(actor)
                outcome = self._outcome()
                if outcome:
                    return self._finish(outcome, bool(bonus_order))
        return self._finish("inconclusive", bool(bonus_order))
