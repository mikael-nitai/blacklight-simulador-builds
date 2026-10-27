"""Small deterministic duel engine.

Coverage is intentionally limited to open-field two-character encounters.
RULES_AUDIT.md gives the rule IDs emitted by the event log. Policies request
actions; this module alone validates and applies their effects.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from random import Random
from typing import Protocol

from .dice import DieRoll, Result, resolve_check
from .pool_damage import roll_damage_pool


class IllegalAction(ValueError):
    pass


@dataclass(frozen=True)
class Profile:
    name: str
    rank: int
    max_health: int
    max_focus: int
    melee: int
    agility: int
    resilience: int
    vigilance: int
    melee_defense: int
    agility_defense: int
    run_speed: int
    health_dr: int = 0
    melee_bonus: int = 0
    ranged_bonus: int = 0
    ranged_range: int = 0
    ranged_is_ammunition: bool = False
    logic: int = 0
    initiative_modifier: int | None = None
    run_speed_exception: bool = False
    powers: frozenset[str] = frozenset()
    traits: frozenset[str] = frozenset()
    weapons: frozenset[str] = frozenset()
    shield_active: bool = False
    heroic: bool = False

    def __post_init__(self) -> None:
        if self.rank < 1 or self.max_health < 1 or self.max_focus < 1:
            raise ValueError("Invalid resource maximum")
        if self.run_speed < 0 or self.health_dr < 0 or self.ranged_range < 0:
            raise ValueError("Invalid movement, reduction, or range")
        if self.melee_defense != 10 + self.melee or self.agility_defense != 10 + self.agility:
            raise ValueError("Defense scores must be derived from abilities in this model")
        if (self.run_speed != 5 + max(0, self.agility // 5)
                and not self.run_speed_exception):
            raise ValueError("Run Speed must be derived from Agility in this model")


def blacklight_profile() -> Profile:
    """Fields from the PDF supplied on 2026-10-26; derived Run/initiative use Core.

    The PDF's derived Initiative +1 and Run 6 conflict with its Vigilance 2 and
    Agility 1. This model uses Vigilance 2 and rule-derived Run 5, and records
    those choices in CHARACTER_AUDIT.md. Available biological weapons are
    listed in `weapons`; their effects are resolved by attack actions.
    """
    return Profile(
        "Blacklight", 3, 150, 90, 6, 1, 5, 2, 16, 11, 5,
        health_dr=1, melee_bonus=3,
        powers=frozenset({"healing_factor", "brawling", "fast_strikes",
                          "attack_stance", "riposte", "do_this_all_day",
                          "blazing_fast_fists", "mighty"}),
        traits=frozenset({"battle_ready", "combat_reflexes", "situational_awareness",
                          "signature_fast_strikes"}),
        weapons=frozenset({"blade", "claw", "hammer", "shield"}),
        heroic=True,
    )


@dataclass
class Fighter:
    profile: Profile
    health: int = field(init=False)
    focus: int = field(init=False)
    stance: bool = False
    shield_active: bool = field(init=False)
    reactions: int = 0
    reacted_to: set[int] = field(default_factory=set)
    damage_dealt: int = 0
    damage_taken: int = 0
    damage_mitigated: int = 0
    healing_effective: int = 0
    focus_spent: int = 0
    attacks: int = 0
    hits: int = 0
    fantastic_hits: int = 0
    ripostes: int = 0
    stuns_applied: int = 0
    blade_bonus_actions: int = 0
    bleeding: int = 0
    stunned_by: int | None = None
    stun_expires_on_actor_turn: int | None = None
    limb_stage: int = 0
    dodging: bool = False
    standard_available: bool = False
    movement_available: bool = False

    def __post_init__(self) -> None:
        self.health = self.profile.max_health
        self.focus = self.profile.max_focus
        self.shield_active = self.profile.shield_active
        self.reactions = 1 + int("combat_reflexes" in self.profile.traits)

    @property
    def conscious(self) -> bool:
        return self.health > 0


@dataclass(frozen=True)
class FighterView:
    name: str
    rank: int
    logic: int
    health: int
    max_health: int
    focus: int
    max_focus: int
    melee_defense: int
    agility_defense: int
    health_dr: int
    run_speed: int
    ranged_range: int
    stance: bool
    reactions: int
    bleeding: int
    stunned: bool
    shield_active: bool
    limb_stage: int
    dodging: bool
    powers: frozenset[str]


@dataclass(frozen=True)
class Observation:
    me: FighterView
    foe: FighterView
    distance: int
    round: int
    bonus_round: bool


@dataclass(frozen=True)
class Move:
    direction: str = "stay"  # stay, approach, retreat
    steps: int = 0


@dataclass(frozen=True)
class Action:
    kind: str  # melee, ranged, fast_strikes, stance, heal, wait
    focus: int = 0
    move: Move | None = None
    offhand: str | None = None


class Policy(Protocol):
    def choose_move(self, observation: Observation) -> Move | None: ...
    def choose_post_move(self, observation: Observation) -> Move: ...
    def choose_action(self, observation: Observation) -> Action: ...
    def use_riposte(self, observation: Observation) -> bool: ...
    def choose_riposte_attack(self, observation: Observation) -> Action: ...
    def choose_blade_bonus(self, observation: Observation) -> Action: ...
    def choose_edge_die(self, roll: DieRoll, modifier: int,
                        target: int, context: str) -> int | None: ...
    def choose_knockback(self, observation: Observation, mode: str) -> bool: ...
    def use_shield_reaction(self, observation: Observation,
                            incoming_kind: str) -> bool: ...
    def use_shield_end_turn(self, observation: Observation) -> bool: ...


@dataclass(frozen=True)
class BattleResult:
    seed: int
    winner: str | None
    outcome: str
    rounds: int
    turns: int
    bonus_round_occurred: bool
    final_health: tuple[int, int]
    final_focus: tuple[int, int]
    metrics: tuple[dict, dict]
    log: tuple[dict, ...]


@dataclass(frozen=True)
class ReactionEvent:
    kind: str
    reactor: int
    source: int
    trigger: int


def blade_second_strike_eligible(first_strike: Result) -> bool:
    """House rule HR-03: only a successful fantastic hit opens a second action."""
    return first_strike.success and first_strike.fantastic


class Duel:
    def __init__(
        self,
        profiles: tuple[Profile, Profile],
        policies: tuple[Policy, Policy],
        *,
        seed: int,
        initial_distance: int = 1,
        max_rounds: int = 30,
        stack_signature_edge: bool = True,
        stack_stunned_edge: bool = False,
        end_turn_healing_first: bool = True,
        audit: bool = False,
    ) -> None:
        if initial_distance < 1 or max_rounds < 1:
            raise ValueError("Distance and horizon must be positive")
        self.fighters = [Fighter(p) for p in profiles]
        self.policies = policies
        self.rng = Random(seed)
        # Independent stream: extra damage dice never change future hit rolls.
        self.damage_rng = Random(seed ^ 0xD6162026)
        self.seed = seed
        self.distance = initial_distance
        self.max_rounds = max_rounds
        self.stack_signature_edge = stack_signature_edge
        self.stack_stunned_edge = stack_stunned_edge
        self.end_turn_healing_first = end_turn_healing_first
        self.audit = audit
        self.log: list[dict] = []
        self.seq = 0
        self.trigger_seq = 0
        self.pending: deque[ReactionEvent] = deque()
        self.round = 0
        self.bonus_round = False
        self.turns = 0
        self.turn_counts = [0, 0]
        self.damage_timeline: dict[int, tuple[int, int]] = {}
        self.active_actor: int | None = None

    def _record(self, kind: str, rules: tuple[str, ...], **data: object) -> None:
        if self.audit:
            self.seq += 1
            self.log.append({"seq": self.seq, "round": self.round,
                             "bonus_round": self.bonus_round, "type": kind,
                             "rules": list(rules), **data})

    @staticmethod
    def _view(f: Fighter) -> FighterView:
        p = f.profile
        return FighterView(p.name, p.rank, p.logic, f.health, p.max_health, f.focus, p.max_focus,
                           p.melee_defense, p.agility_defense, p.health_dr,
                           p.run_speed, p.ranged_range, f.stance, f.reactions,
                           f.bleeding, f.stunned_by is not None, f.shield_active,
                           f.limb_stage, f.dodging,
                           p.powers)

    def observe(self, actor: int) -> Observation:
        return Observation(self._view(self.fighters[actor]),
                           self._view(self.fighters[1 - actor]), self.distance,
                           self.round, self.bonus_round)

    def _move(self, actor: int, move: Move, *, as_standard: bool = False) -> None:
        f = self.fighters[actor]
        if self.active_actor != actor or not f.conscious or f.stunned_by is not None:
            raise IllegalAction("Movement outside actor's turn")
        if as_standard and not f.standard_available:
            raise IllegalAction("Standard action is not available for movement")
        if not as_standard and not f.movement_available:
            raise IllegalAction("Movement action is not available")
        if move.direction not in ("stay", "approach", "retreat"):
            raise IllegalAction("Unknown movement direction")
        if not 0 <= move.steps <= f.profile.run_speed:
            raise IllegalAction("Movement exceeds Run Speed")
        if move.direction == "stay" and move.steps != 0:
            raise IllegalAction("Stay movement has steps")
        if as_standard:
            f.standard_available = False
        else:
            f.movement_available = False
        before = self.distance
        if move.direction == "approach":
            self.distance = max(1, self.distance - move.steps)
        elif move.direction == "retreat":
            self.distance += move.steps
        self._record("movement", ("ACT-01", "ACT-06"), actor=f.profile.name,
                     direction=move.direction, steps=move.steps,
                     as_standard=as_standard,
                     distance_before=before, distance_after=self.distance)

    def legal_actions(self, actor: int) -> tuple[Action, ...]:
        f = self.fighters[actor]
        if (self.active_actor != actor or not f.conscious or
                f.stunned_by is not None or not f.standard_available):
            return ()
        p = f.profile
        legal = [Action("wait"), Action("move"), Action("dodge")]
        if "shield" in p.weapons and not f.shield_active:
            legal.append(Action("shield"))
        if self.distance <= 1:
            legal.append(Action("melee"))
            if "fast_strikes" in p.powers:
                legal.append(Action("fast_strikes"))
            for weapon in ("blade", "claw", "hammer"):
                if weapon not in p.weapons:
                    continue
                legal.append(Action(weapon))
                if "fast_strikes" in p.powers:
                    legal.append(Action(f"{weapon}_fast"))
                    for other in sorted(p.weapons - {weapon}):
                        if other == "shield":
                            continue
                        legal.append(Action(f"{weapon}_fast", offhand=other))
        if p.ranged_range and self.distance <= p.ranged_range * 2:
            legal.append(Action("ranged"))
        if "attack_stance" in p.powers and not f.stance:
            legal.append(Action("stance"))
        if "do_this_all_day" in p.powers:
            for spent in range(5, min(5 * p.rank, f.focus - 1) + 1):
                legal.append(Action("heal", spent))
        if f.bleeding:
            legal.append(Action("treat_bleeding"))
        return tuple(legal)

    def _heal(self, actor: int, amount: int, rule: str) -> None:
        f = self.fighters[actor]
        before = f.health
        f.health = min(f.profile.max_health, f.health + amount)
        effective = f.health - before
        f.healing_effective += effective
        if effective >= 1 and f.bleeding:
            previous = f.bleeding
            f.bleeding = 0
            self._record("condition_end", ("COND-01", rule), actor=f.profile.name,
                         condition="bleeding", prior_intensity=previous)
        self._record("heal", (rule,), actor=f.profile.name,
                     proposed=amount, effective=effective,
                     health_before=before, health_after=f.health)

    def _attack(self, actor: int, kind: str, *, reaction: bool = False,
                offhand: str | None = None) -> Result:
        attacker, defender = self.fighters[actor], self.fighters[1 - actor]
        p, q = attacker.profile, defender.profile
        ranged = kind == "ranged"
        fast = kind == "fast_strikes" or kind.endswith("_fast")
        primary = kind[:-5] if kind.endswith("_fast") else kind
        weapons_used = ({primary} if primary in {"blade", "claw", "hammer"} else set())
        if offhand:
            if offhand == "shield":
                raise IllegalAction("Shield is a separate defensive action, not a Fast Strikes weapon")
            weapons_used.add(offhand)
        blade = "blade" in weapons_used
        claw = "claw" in weapons_used
        hammer = "hammer" in weapons_used
        if offhand and not fast:
            raise IllegalAction("Two offensive weapons require Fast Strikes")
        if attacker.shield_active:
            attacker.shield_active = False
            self._record("shield_deactivate", ("HR-04",), actor=p.name,
                         cost="free", reason="attack")
        if ranged:
            if not p.ranged_range or self.distance > p.ranged_range * 2:
                raise IllegalAction("Ranged target outside permitted range")
            modifier = p.agility
            target = q.melee_defense if "brawling" in q.powers else q.agility_defense
            edges = 0
            troubles = int(self.distance > p.ranged_range)
            bonus = p.ranged_bonus
            rules = ("ACT-05", "DMG-01", "POW-04") if "brawling" in q.powers else ("ACT-05", "DMG-01")
        else:
            if self.distance > 1:
                raise IllegalAction("Close target out of reach")
            modifier, target = p.melee, q.melee_defense
            edges = int("blazing_fast_fists" in p.powers)
            if fast and "signature_fast_strikes" in p.traits:
                edges = edges + 1 if self.stack_signature_edge else max(1, edges)
            troubles = 0
            bonus = p.melee_bonus
            rules = ("ACT-05", "DMG-01", "POW-05", "HR-06") if fast and offhand else (("ACT-05", "DMG-01", "POW-05") if fast else ("ACT-05", "DMG-01"))
            if blade:
                rules += ("HR-03",)
            if claw:
                rules += ("HR-01",)
            if edges:
                rules += ("POW-08",)
            if hammer:
                rules += ("HR-02",)
        if defender.stunned_by is not None:
            edges = edges + 1 if self.stack_stunned_edge else max(1, edges)
            rules += ("COND-02",)
        if defender.dodging:
            troubles += 1
            rules += ("ACT-07",)
        ability_for_damage = modifier * (2 if attacker.stance and not ranged else 1)
        first_weapon = ("ranged" if ranged else
                        primary if primary in {"blade", "claw", "hammer"}
                        else "bare")
        strike_weapons = ([first_weapon, offhand or first_weapon]
                          if fast else [first_weapon])

        def component_bonuses(weapon: str) -> list[int]:
            if weapon == "hammer":
                return [bonus + 2] if "mighty" in p.powers else [bonus, 2]
            if weapon in {"blade", "claw"}:
                # HR-01/03 as subsequently clarified: +1 stacks with Mighty.
                return [bonus + 1] if "mighty" in p.powers else [bonus, 1]
            return [bonus]

        component_specs = [(weapon, component_bonuses(weapon))
                           for weapon in strike_weapons]
        bonuses = component_specs[0][1]
        result, rerolls = resolve_check(
            self.rng, modifier, target, edges=edges, troubles=troubles,
            chooser=lambda roll, mod, tn: self.policies[actor].choose_edge_die(
                roll, mod, tn, kind))
        self.trigger_seq += 1
        trigger = self.trigger_seq
        if (result.success and not defender.shield_active
                and "shield" in q.weapons and defender.conscious
                and defender.stunned_by is None and defender.reactions > 0
                and trigger not in defender.reacted_to
                and self.policies[1 - actor].use_shield_reaction(
                    self.observe(1 - actor), kind)):
            defender.reactions -= 1
            defender.reacted_to.add(trigger)
            defender.shield_active = True
            self._record("reaction_spent", ("ACT-03", "ACT-04", "HR-04"),
                         actor=q.name, trigger=trigger,
                         remaining=defender.reactions)
            self._record("shield_activate", ("HR-04",),
                         actor=q.name, cost="reaction", trigger=trigger,
                         after_hit=True)
        shield_applies = defender.shield_active and (not ranged or q.rank >= 2)
        reduction = q.health_dr + (2 if shield_applies else 0)
        if shield_applies:
            rules += ("HR-04",)
        ammo_immunity = bool(ranged and defender.shield_active and q.rank >= 3
                             and p.ranged_is_ammunition)
        knockback_eligible = bool(result.success and result.fantastic
                                  and not ranged and not fast
                                  and "mighty" in p.powers)
        knockback_selected = (self.policies[actor].choose_knockback(
            self.observe(actor), kind) if knockback_eligible else False)
        attacker.attacks += 1
        before = defender.health
        damage = 0
        raw_damage = 0
        damage_components: list[dict] = []
        if result.success:
            attacker.hits += 1
            if result.fantastic:
                attacker.fantastic_hits += 1
            if ammo_immunity:
                rules += ("HR-04",)
            for weapon, candidates in component_specs:
                full_multiplier = p.rank + max(0, *candidates)
                pool = roll_damage_pool(
                    self.damage_rng, full_multiplier=full_multiplier,
                    ability=ability_for_damage,
                    reduction=0 if ammo_immunity else reduction,
                    fast_strikes=fast, fantastic=result.fantastic,
                    sample_counterfactual=not ammo_immunity)
                applied_component = 0 if ammo_immunity else pool.damage
                raw_component = (pool.damage if ammo_immunity else
                                 pool.damage_without_reduction)
                damage += applied_component
                raw_damage += raw_component or 0
                damage_components.append({
                    "weapon": weapon, "bonus_candidates": candidates,
                    "full_multiplier": full_multiplier,
                    "reduction": reduction,
                    "dice_after_reduction": pool.dice_after_reduction,
                    "dice_rolled": pool.dice_rolled,
                    "ability_added": pool.ability_added,
                    "faces": list(pool.faces),
                    "counterfactual_faces": list(pool.counterfactual_faces),
                    "ammunition_immunity": ammo_immunity,
                    "damage": applied_component,
                    "damage_without_reduction": raw_component,
                })
            defender.damage_mitigated += max(0, raw_damage - damage)
            defender.health -= damage
            if p.heroic and defender.health <= -q.max_health:
                defender.health = -q.max_health + 1
            applied = before - defender.health
            attacker.damage_dealt += applied
            defender.damage_taken += applied
            if blade or (claw and result.fantastic and not knockback_selected):
                # The same condition never stacks; see FAQ 2025 p.2.
                defender.bleeding = max(defender.bleeding, 5)
                self._record("condition_start", ("COND-01", "HR-03" if blade else "HR-01"),
                             actor=q.name, condition="bleeding", intensity=5)
            if blade and result.fantastic and not knockback_selected:
                defender.limb_stage = min(2, defender.limb_stage + 1)
                self._record("limb_effect", ("HR-03",),
                             actor=p.name, target=q.name,
                             stage=defender.limb_stage,
                             mechanical_penalty="unmodeled")
            if hammer and result.fantastic and not knockback_selected:
                attacker.stuns_applied += 1
                defender.stunned_by = actor
                defender.stun_expires_on_actor_turn = self.turn_counts[actor] + 1
                defender.stance = False
                self._record("condition_start", ("HR-02", "COND-02"),
                             actor=q.name, condition="stunned",
                             expires_on_actor=p.name,
                             source_turn_count=defender.stun_expires_on_actor_turn)
            if defender.health <= 0:
                defender.stance = False
        self._record("attack", rules + (("POW-06",) if reaction else ()),
                     actor=p.name, target=q.name, mode=kind, offhand=offhand,
                     reaction=reaction,
                     trigger=trigger, distance=self.distance,
                     roll=[result.roll.left, result.roll.marvel, result.roll.right],
                     rerolls=[vars(x) for x in rerolls], total=result.total,
                     check_modifier=modifier, edges=edges, troubles=troubles,
                     target_number=target, success=result.success,
                     fantastic=result.fantastic, ultimate=result.ultimate,
                     rank=p.rank, ability_for_damage=ability_for_damage,
                     bonus_candidates=bonuses, reduction=reduction,
                     damage_denominator=(1 if result.fantastic else 2) if fast else 1,
                     default_fantastic_multiplier=not fast,
                     damage_model="literal_marvel_pool_v2",
                     damage_components=damage_components,
                     strike_weapons=strike_weapons,
                     ammunition_immunity=ammo_immunity,
                     knockback_selected=knockback_selected,
                     calculated_damage=damage, damage=before - defender.health,
                     health_before=before, health_after=defender.health)
        if knockback_eligible:
            if knockback_selected:
                effective_multiplier = max(0, p.rank + max(0, *bonuses) - reduction)
                spaces = 5 * effective_multiplier
                if spaces:
                    prior_distance = self.distance
                    self.distance += spaces
                    defender.stance = False
                    self._record("knockback", ("POW-01", "DMG-03"),
                                 actor=p.name, target=q.name, spaces=spaces,
                                 distance_before=prior_distance,
                                 distance_after=self.distance,
                                 concentration_broken=True)
            else:
                self._record("knockback_declined", ("POW-01",),
                             actor=p.name, target=q.name)
        if not result.success and not ranged:
            self.pending.append(ReactionEvent("riposte", 1 - actor, actor, trigger))
            self._record("reaction_queued", ("ACT-03", "POW-06"),
                         actor=q.name, trigger=trigger, source=p.name)
        return result

    def _drain_events(self) -> None:
        processed = 0
        while self.pending:
            processed += 1
            if processed > 16:
                raise RuntimeError("Reaction queue exceeded safety bound")
            event = self.pending.popleft()
            if event.kind != "riposte":
                raise RuntimeError("Unrecognized pending event")
            defender = self.fighters[event.reactor]
            if ("riposte" not in defender.profile.powers or not defender.conscious
                    or defender.stunned_by is not None
                    or defender.reactions < 1 or event.trigger in defender.reacted_to
                    or self.distance > 1):
                continue
            if not self.policies[event.reactor].use_riposte(self.observe(event.reactor)):
                continue
            defender.reactions -= 1
            defender.reacted_to.add(event.trigger)
            defender.ripostes += 1
            self._record("reaction_spent", ("ACT-03", "ACT-04", "POW-06"),
                         actor=defender.profile.name, trigger=event.trigger,
                         remaining=defender.reactions)
            chosen = self.policies[event.reactor].choose_riposte_attack(
                self.observe(event.reactor))
            if (chosen.focus != 0 or chosen.offhand is not None or
                    chosen.kind not in ("melee", "blade", "claw", "hammer") or
                    (chosen.kind != "melee" and
                     chosen.kind not in defender.profile.weapons)):
                raise IllegalAction("Riposte policy selected an invalid close attack")
            self._attack(event.reactor, chosen.kind, reaction=True)

    def _act(self, actor: int, action: Action) -> None:
        if action.kind == "move":
            if action.move is None or action.focus != 0:
                raise IllegalAction("Standard movement requires a movement request")
            self._move(actor, action.move, as_standard=True)
            return
        if action not in self.legal_actions(actor):
            raise IllegalAction(f"Illegal standard action: {action}")
        f = self.fighters[actor]
        f.standard_available = False
        attack_kinds = {"melee", "ranged", "fast_strikes", "blade", "blade_fast",
                        "claw", "claw_fast", "hammer", "hammer_fast"}
        if action.kind in attack_kinds:
            result = self._attack(actor, action.kind, offhand=action.offhand)
            self._drain_events()
            blade_used = (action.kind in ("blade", "blade_fast")
                          or action.offhand == "blade")
            if (blade_used
                    and blade_second_strike_eligible(result)
                    and self.fighters[1 - actor].conscious and f.conscious):
                bonus = self.policies[actor].choose_blade_bonus(self.observe(actor))
                bonus_blade = (bonus.kind in ("blade", "blade_fast")
                               or bonus.offhand == "blade")
                if (not bonus_blade or bonus.kind not in attack_kinds
                        or bonus not in self._blade_bonus_actions(actor)):
                    raise IllegalAction("Blade bonus must be one blade attack")
                self._record("blade_bonus", ("HR-03",), actor=f.profile.name,
                             chosen=bonus.kind, offhand=bonus.offhand)
                f.blade_bonus_actions += 1
                self._attack(actor, bonus.kind, offhand=bonus.offhand)
                self._drain_events()
        elif action.kind == "stance":
            f.stance = True
            self._record("stance", ("POW-09",), actor=f.profile.name,
                         active=True)
        elif action.kind == "shield":
            f.shield_active = True
            self._record("shield_activate", ("HR-04",),
                         actor=f.profile.name, cost="standard")
        elif action.kind == "dodge":
            f.dodging = True
            self._record("dodge", ("ACT-07",), actor=f.profile.name,
                         active_until_next_turn=True)
        elif action.kind == "treat_bleeding":
            result, rerolls = resolve_check(
                self.rng, f.profile.logic, 10,
                chooser=lambda roll, mod, tn: self.policies[actor].choose_edge_die(
                    roll, mod, tn, "treat_bleeding"))
            prior_intensity = f.bleeding
            if result.success:
                f.bleeding = 0
            self._record("condition_treatment", ("COND-01", "D616-01"),
                         actor=f.profile.name, condition="bleeding",
                         roll=[result.roll.left, result.roll.marvel, result.roll.right],
                         rerolls=[vars(x) for x in rerolls],
                         check_modifier=f.profile.logic, total=result.total,
                         target_number=10, fantastic=result.fantastic,
                         ultimate=result.ultimate, success=result.success,
                         prior_intensity=prior_intensity,
                         remaining_intensity=f.bleeding)
        elif action.kind == "heal":
            if action.focus > 5 * f.profile.rank or f.focus - action.focus < 1:
                raise IllegalAction("Focus spending cap exceeded")
            before = f.focus
            f.focus -= action.focus
            f.focus_spent += action.focus
            self._record("focus_spent", ("RES-01", "POW-07"),
                         actor=f.profile.name, amount=action.focus,
                         focus_before=before, focus_after=f.focus)
            self._heal(actor, 2 * action.focus, "POW-07")
        else:
            self._record("wait", ("ACT-01",), actor=f.profile.name)

    def _blade_bonus_actions(self, actor: int) -> tuple[Action, ...]:
        p = self.fighters[actor].profile
        if self.distance > 1 or "blade" not in p.weapons:
            return ()
        choices = [Action("blade")]
        if "fast_strikes" in p.powers:
            for primary in ("blade", "claw", "hammer"):
                if primary not in p.weapons:
                    continue
                if primary == "blade":
                    choices.append(Action("blade_fast"))
                    others = p.weapons - {"blade"}
                else:
                    others = {"blade"}
                for other in sorted(others):
                    if other == "shield":
                        continue
                    choices.append(Action(f"{primary}_fast", offhand=other))
        return tuple(choices)

    def _turn(self, actor: int) -> None:
        f = self.fighters[actor]
        if not f.conscious:
            return
        if self.active_actor is not None:
            raise RuntimeError("Nested turn")
        self.active_actor = actor
        self.turn_counts[actor] += 1
        if f.dodging:
            f.dodging = False
            self._record("dodge_end", ("ACT-07",), actor=f.profile.name)
        for other in self.fighters:
            if (other.stunned_by == actor and
                    other.stun_expires_on_actor_turn is not None and
                    self.turn_counts[actor] >= other.stun_expires_on_actor_turn):
                other.stunned_by = None
                other.stun_expires_on_actor_turn = None
                self._record("condition_end", ("COND-02",),
                             actor=other.profile.name, condition="stunned")
        f.standard_available = True
        f.movement_available = True
        self.turns += 1
        self._record("turn_start", ("ACT-01", "ACT-04"), actor=f.profile.name,
                     reactions=f.reactions)
        try:
            if f.stunned_by is not None:
                self._record("turn_skipped", ("COND-02",), actor=f.profile.name,
                             reason="stunned")
            else:
                move = self.policies[actor].choose_move(self.observe(actor))
                if move is not None:
                    self._move(actor, move)
                action = self.policies[actor].choose_action(self.observe(actor))
                self._act(actor, action)
                if f.movement_available and f.conscious:
                    self._move(actor, self.policies[actor].choose_post_move(self.observe(actor)))
            if self.end_turn_healing_first and "healing_factor" in f.profile.powers:
                self._heal(actor, f.profile.resilience, "POW-03")
            if f.bleeding:
                before = f.health
                inflicted = max(0, f.bleeding - 5 * f.profile.health_dr)
                f.health -= inflicted
                f.damage_taken += inflicted
                self._record("condition_tick", ("COND-01", "POW-02"),
                             actor=f.profile.name, condition="bleeding",
                             intensity=f.bleeding, damage=inflicted,
                             health_before=before, health_after=f.health)
            if not self.end_turn_healing_first and "healing_factor" in f.profile.powers:
                self._heal(actor, f.profile.resilience, "POW-03")
            if (f.conscious and f.stunned_by is None and not f.shield_active
                    and "shield" in f.profile.weapons and f.reactions > 0
                    and self.policies[actor].use_shield_end_turn(
                        self.observe(actor))):
                f.reactions -= 1
                f.shield_active = True
                self._record("reaction_spent", ("ACT-03", "ACT-04", "HR-04"),
                             actor=f.profile.name, source="end_turn",
                             remaining=f.reactions)
                self._record("shield_activate", ("HR-04",),
                             actor=f.profile.name, cost="reaction",
                             timing="end_turn")
            self._record("turn_end", ("ACT-01",), actor=f.profile.name,
                         health=f.health, focus=f.focus)
            self.damage_timeline[self.round] = (
                self.fighters[0].damage_dealt, self.fighters[1].damage_dealt)
        finally:
            f.standard_available = False
            f.movement_available = False
            self.active_actor = None

    def _initiative(self) -> tuple[tuple[int, ...], tuple[bool, bool]]:
        checks = []
        modifiers = []
        for i, f in enumerate(self.fighters):
            edges = int("situational_awareness" in f.profile.traits)
            modifier = (f.profile.initiative_modifier
                        if f.profile.initiative_modifier is not None
                        else f.profile.vigilance)
            modifiers.append(modifier)
            result, rerolls = resolve_check(
                self.rng, modifier, target=0, edges=edges,
                chooser=lambda roll, mod, tn: self.policies[i].choose_edge_die(
                    roll, mod, tn, "initiative"))
            checks.append(result)
            self._record("initiative", ("ACT-02", "TRT-03", "D616-01"),
                         actor=f.profile.name, roll=[result.roll.left,
                         result.roll.marvel, result.roll.right],
                         rerolls=[vars(x) for x in rerolls], total=result.total,
                         modifier=modifier,
                         fantastic=result.fantastic)
        order = tuple(sorted(range(2), key=lambda i: (-checks[i].total,
                           -int(checks[i].fantastic), -modifiers[i],
                           i)))
        return order, (checks[0].fantastic, checks[1].fantastic)

    def _outcome(self) -> tuple[str, str | None] | None:
        a, b = self.fighters
        if a.conscious and b.conscious:
            return None
        if not a.conscious and not b.conscious:
            return "draw", None
        return ("win", a.profile.name) if a.conscious else ("win", b.profile.name)

    def _finish(self, outcome: str, winner: str | None,
                bonus_occurred: bool) -> BattleResult:
        a, b = self.fighters
        def metrics(f: Fighter) -> dict:
            index = 0 if f is a else 1
            def damage_by(horizon: int) -> int:
                if self.round <= horizon:
                    return f.damage_dealt
                return self.damage_timeline[horizon][index]
            return {"damage_dealt": f.damage_dealt, "damage_taken": f.damage_taken,
                    "damage_mitigated": f.damage_mitigated,
                    "healing_effective": f.healing_effective,
                    "focus_spent": f.focus_spent, "attacks": f.attacks,
                    "hits": f.hits, "fantastic_hits": f.fantastic_hits,
                    "ripostes": f.ripostes, "stuns_applied": f.stuns_applied,
                    "blade_bonus_actions": f.blade_bonus_actions,
                    "damage_round3": damage_by(3),
                    "damage_round5": damage_by(5),
                    "damage_round10": damage_by(10)}
        return BattleResult(self.seed, winner, outcome, self.round, self.turns,
                            bonus_occurred, (a.health, b.health),
                            (a.focus, b.focus), (metrics(a), metrics(b)),
                            tuple(self.log))

    def run(self) -> BattleResult:
        order, fantastics = self._initiative()
        bonus = tuple(i for i in order if fantastics[i])
        if bonus:
            self.round = 0
            self.bonus_round = True
            self._reset_reactions_for_round()
            for actor in bonus:
                self._turn(actor)
                outcome = self._outcome()
                if outcome:
                    return self._finish(*outcome, True)
        self.bonus_round = False
        for round_number in range(1, self.max_rounds + 1):
            self.round = round_number
            self._reset_reactions_for_round()
            for actor in order:
                self._turn(actor)
                outcome = self._outcome()
                if outcome:
                    return self._finish(*outcome, bool(bonus))
        return self._finish("inconclusive", None, bool(bonus))

    def _reset_reactions_for_round(self) -> None:
        for fighter in self.fighters:
            fighter.reactions = 1 + int("combat_reflexes" in fighter.profile.traits)
            fighter.reacted_to.clear()
            self._record("reaction_reset", ("ACT-03", "ACT-04"),
                         actor=fighter.profile.name,
                         reactions=fighter.reactions)
