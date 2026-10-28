"""Two-check Fast Strikes with one limb selected for effects before the use.

This is the current table contract. The existing Duel/ModularDuel remain
available for explicitly versioned historical replays.
"""

from dataclasses import dataclass

from blacklight.engine import Action, FastStrikeContext, IllegalAction, PreparedAttackCheck
from blacklight.policies import RulePolicy
from blacklight.rulesets import CURRENT_RULESET
from .modular_duel import ModularDuel


ATTACK_KINDS = frozenset({'melee', 'ranged', 'fast_strikes', 'blade', 'blade_fast',
                          'claw', 'claw_fast', 'hammer', 'hammer_fast'})


def is_fast(kind: str) -> bool:
    return kind == 'fast_strikes' or kind.endswith('_fast')


@dataclass(frozen=True)
class FastAction(Action):
    effect_limb: int | None = None
    targets: tuple[int, int] | None = None

    def __post_init__(self) -> None:
        if (not isinstance(self.kind, str) or not is_fast(self.kind)
                or type(self.effect_limb) is not int or self.effect_limb not in (0, 1)
                or type(self.focus) is not int or self.focus != 0 or self.move is not None
                or self.targets is not None and
                (not isinstance(self.targets, tuple) or len(self.targets) != 2
                 or any(type(target) is not int or target < 0 for target in self.targets))
                or self.offhand is not None and self.offhand not in ('blade', 'claw', 'hammer')):
            raise ValueError('Fast Strikes requires a preselected effect limb and no extra cost')


@dataclass(frozen=True)
class SplitFastPolicy(RulePolicy):
    effect_limb: int = 0

    def __post_init__(self) -> None:
        if type(self.effect_limb) is not int or self.effect_limb not in (0, 1):
            raise ValueError('Choose the effect limb before resolving Fast Strikes')

    def _select_effects(self, request: Action) -> Action:
        if is_fast(request.kind):
            return FastAction(request.kind, offhand=request.offhand, effect_limb=self.effect_limb)
        return request

    def choose_action(self, observation) -> Action:
        return self._select_effects(super().choose_action(observation))

    def choose_blade_bonus(self, observation) -> Action:
        return self._select_effects(super().choose_blade_bonus(observation))


class SplitFastDuel(ModularDuel):
    table_ruleset = CURRENT_RULESET

    def __init__(self, *args, **kwargs) -> None:
        if kwargs.get('stack_signature_edge', True) is not True:
            raise ValueError('The current table confirmed both Fast Strikes edge sources')
        if kwargs.get('fast_zero_dice_bonus', True) is not True:
            raise ValueError('The current table preserves the bonus when Fast halves one die to zero')
        kwargs['fast_zero_dice_bonus'] = True
        super().__init__(*args, **kwargs)
        self.fast_use_seq = 0

    @staticmethod
    def _with_effect_choices(actions: tuple[Action, ...]) -> tuple[Action, ...]:
        result = []
        for action in actions:
            if is_fast(action.kind):
                result.extend(FastAction(action.kind, offhand=action.offhand, effect_limb=limb)
                              for limb in (0, 1))
            else:
                result.append(action)
        return tuple(result)

    def legal_actions(self, actor: int) -> tuple[Action, ...]:
        return self._with_effect_choices(super().legal_actions(actor))

    def _blade_bonus_actions(self, actor: int) -> tuple[Action, ...]:
        return self._with_effect_choices(super()._blade_bonus_actions(actor))

    def _attack(self, actor: int, kind: str, *, reaction: bool = False,
                offhand: str | None = None, fast_strike: FastStrikeContext | None = None,
                prepared_check: PreparedAttackCheck | None = None,
                target_actor: int | None = None):
        if is_fast(kind) and fast_strike is None:
            raise IllegalAction('Fast Strikes must declare both limbs and its effect choice first')
        return super()._attack(actor, kind, reaction=reaction, offhand=offhand,
                               fast_strike=fast_strike, prepared_check=prepared_check,
                               target_actor=target_actor)

    def _fast_targets(self, actor: int, action: FastAction) -> tuple[int, int]:
        targets = action.targets or (self._target_index(actor),) * 2
        for target in targets:
            self._target_index(actor, target)
            if not self.fighters[target].conscious:
                raise IllegalAction('Declare conscious enemy targets before the Fast use')
        return targets

    def _attack_targets_available(self, actor: int) -> bool:
        return self.fighters[self._target_index(actor)].conscious and self.distance <= 1

    def _fast_use(self, actor: int, action: FastAction, *, bonus_action: bool) -> tuple[bool, int]:
        targets = self._fast_targets(actor, action)
        first = action.kind[:-5] if action.kind.endswith('_fast') else 'bare'
        weapons = (first, action.offhand or first)
        self.fast_use_seq += 1
        use_id = self.fast_use_seq
        attacker = self.fighters[actor]
        target_names = [self.fighters[target].profile.name for target in targets]
        self._record('fast_use_start', ('HR-09', 'ACT-01'),
                     actor=attacker.profile.name, target=target_names[0],
                     fast_use_id=use_id, weapons=list(weapons),
                     effect_limb=action.effect_limb, bonus_action=bonus_action,
                     **({'targets': target_names} if action.targets is not None else {}))
        if attacker.shield_active:
            attacker.shield_active = False
            self._record('shield_deactivate', ('HR-04',), actor=attacker.profile.name,
                         cost='free', reason='attack')
        modes = tuple('fast_strikes' if weapon == 'bare' else f'{weapon}_fast' for weapon in weapons)
        specs = tuple(self._attack_check_spec(actor, mode, targets[limb])
                      for limb, mode in enumerate(modes))
        checks = []
        for limb, mode in enumerate(modes):
            check = self._prepare_attack_check(actor, mode, specs[limb], target_actor=targets[limb])
            checks.append(check)
            result, spec = check.result, check.spec
            self._record('fast_limb_check', ('HR-09', 'D616-01'),
                         actor=attacker.profile.name, target=target_names[limb],
                         fast_use_id=use_id, limb=limb, weapon=weapons[limb],
                         trigger=check.trigger, roll=[result.roll.left, result.roll.marvel, result.roll.right],
                         rerolls=[vars(item) for item in check.rerolls],
                         modifier=spec.modifier, target_number=spec.target,
                         edges=spec.edges, troubles=spec.troubles,
                         total=result.total, success=result.success,
                         fantastic=result.fantastic, ultimate=result.ultimate)
        # The table resolves both checks before effects/reactions. Shield is the
        # defensive exception: after confirmed hits and before either damage.
        for check in checks:
            self._shield_reaction_after_check(actor, check)
        eligible = False
        for limb, (weapon, mode, check) in enumerate(zip(weapons, modes, checks)):
            self._record('fast_limb_start', ('HR-09',), actor=attacker.profile.name,
                         fast_use_id=use_id, limb=limb, weapon=weapon)
            result = self._attack(actor, mode,
                                  fast_strike=FastStrikeContext(use_id, limb, action.effect_limb,
                                                                shield_handled=True),
                                  prepared_check=check, target_actor=targets[limb])
            if (limb == action.effect_limb and weapon == 'blade'
                    and result.success and result.fantastic):
                eligible = True
        self._record('fast_use_end', ('HR-09',), actor=attacker.profile.name,
                     fast_use_id=use_id, completed_limbs=2,
                     blade_bonus_eligible=eligible)
        self._drain_events()
        return eligible, use_id

    def _resolve_attack_action(self, actor: int, action: Action, *, bonus_action: bool):
        if is_fast(action.kind):
            return self._fast_use(actor, action, bonus_action=bonus_action)
        result = self._attack(actor, action.kind, offhand=action.offhand,
                              target_actor=getattr(action, 'target_actor', None))
        self._drain_events()
        return action.kind == 'blade' and result.success and result.fantastic, None

    def _act(self, actor: int, action: Action) -> None:
        if (not isinstance(action, Action) or not isinstance(action.kind, str)
                or type(action.focus) is not int):
            raise IllegalAction('Invalid standard action request')
        if action.kind not in ATTACK_KINDS:
            return super()._act(actor, action)
        if (is_fast(action.kind) and not isinstance(action, FastAction)
                or action not in self.legal_actions(actor)):
            raise IllegalAction('Attack or predeclared effect choice is not legal')
        fighter = self.fighters[actor]
        fighter.standard_available = False
        eligible, source_use = self._resolve_attack_action(actor, action, bonus_action=False)
        if (not eligible or not fighter.conscious or fighter.stunned_by is not None
                or not self._attack_targets_available(actor)):
            return
        bonus = self.policies[actor].choose_blade_bonus(self.observe(actor))
        if (not isinstance(bonus, Action) or type(bonus.focus) is not int
                or bonus not in self._blade_bonus_actions(actor)):
            raise IllegalAction('Blade bonus requires one legal Blade action and an effect choice')
        self._record('blade_bonus', ('HR-03', 'HR-09'), actor=fighter.profile.name,
                     chosen=bonus.kind, offhand=bonus.offhand, source_fast_use=source_use)
        fighter.blade_bonus_actions += 1
        # Never recurse: a Fantastic in this action cannot grant a third action.
        self._resolve_attack_action(actor, bonus, bonus_action=True)
