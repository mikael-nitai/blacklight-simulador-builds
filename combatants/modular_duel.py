"""Progressive action-module adapter around the validated physical Duel.

Focus-paid self-healing, standard state activations and start-turn expiration
are migrated. Attack effects and reactions still use the existing resolver.
"""

from blacklight.engine import Action, Duel, IllegalAction
from .actions import (ActionContext, ActionPlan, ActionRegistry, ActivateState,
                      CombatState, DEFAULT_ACTIONS, RestoreHealth, valid_references)
from .lifecycle import Boundary, TimePoint, TimedEffect, expiration_plan


class ModularDuel(Duel):
    def __init__(self, *args, action_registry: ActionRegistry = DEFAULT_ACTIONS,
                 **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.action_registry = action_registry

    def _start_turn_effects(self, actor: int) -> None:
        """Project existing flags into immutable expiry candidates at this boundary.

        Dodge's flag means "until my next turn"; the hook is called only after
        that owner's turn counter advances. Stunned already stores its source
        and deadline. These fields remain the authoritative state during this
        migration; there is no second mutable effect store to drift out of sync.
        """
        now = TimePoint(Boundary.TURN_START, self.turn_counts[actor], actor)
        effects = []
        if self.fighters[actor].dodging:
            effects.append(TimedEffect(f'dodge:{actor}', 'dodge', actor, actor,
                                       (now,), ('ACT-07',)))
        for subject, fighter in enumerate(self.fighters):
            if fighter.stunned_by is None:
                continue
            deadlines = (() if fighter.stun_expires_on_actor_turn is None else
                         (TimePoint(Boundary.TURN_START,
                                    fighter.stun_expires_on_actor_turn,
                                    fighter.stunned_by),))
            effects.append(TimedEffect(f'stunned:{subject}', 'stunned', subject,
                                       fighter.stunned_by, deadlines, ('COND-02',)))
        plan = expiration_plan(tuple(effects), now)
        for effect in plan.expired:
            fighter = self.fighters[effect.subject]
            if effect.kind == 'dodge':
                fighter.dodging = False
                self._record('dodge_end', effect.rules, actor=fighter.profile.name)
            else:
                fighter.stunned_by = None
                fighter.stun_expires_on_actor_turn = None
                self._record('condition_end', effect.rules,
                             actor=fighter.profile.name, condition='stunned')

    def _action_context(self, actor: int) -> ActionContext:
        fighter = self.fighters[actor]
        profile = fighter.profile
        return ActionContext(profile.rank, fighter.health, profile.max_health,
                             fighter.focus, profile.powers, profile.traits,
                             profile.weapons,
                             frozenset(state for state in CombatState
                                       if getattr(fighter, state.value)))

    @staticmethod
    def _module_actions(module, context: ActionContext) -> tuple[Action, ...]:
        requests = module.available(context)
        if (not isinstance(requests, tuple)
                or any(not isinstance(request, Action) or request.kind != module.kind
                       or type(request.focus) is not int
                       or not 0 <= request.focus <= 5 * context.rank
                       or request.focus > 0 and context.focus - request.focus < 1
                       or request.offhand is not None or request.move is not None
                       for request in requests)):
            raise IllegalAction('Action module emitted requests outside its declared contract')
        if len(set(requests)) != len(requests):
            raise IllegalAction('Action module emitted duplicate requests')
        return requests

    def legal_actions(self, actor: int) -> tuple[Action, ...]:
        fighter = self.fighters[actor]
        if (self.active_actor != actor or not fighter.conscious or
                fighter.stunned_by is not None or not fighter.standard_available):
            return ()
        context = self._action_context(actor)
        base = super().legal_actions(actor)
        result = []
        emitted = set()
        for action in base:
            module = self.action_registry.get(action.kind)
            if module is None:
                result.append(action)
            elif action.kind not in emitted:
                if context.meets(module.requirements):
                    result.extend(self._module_actions(module, context))
                emitted.add(action.kind)
        for kind, module in self.action_registry.modules.items():
            if kind not in emitted:
                if context.meets(module.requirements):
                    result.extend(self._module_actions(module, context))
        return tuple(result)

    def _act(self, actor: int, action: Action) -> None:
        if (not isinstance(action, Action) or not isinstance(action.kind, str)
                or not action.kind.strip() or type(action.focus) is not int):
            raise IllegalAction('Action request has invalid field types')
        module = self.action_registry.get(action.kind)
        if module is None:
            super()._act(actor, action)
            return
        if action not in self.legal_actions(actor):
            raise IllegalAction(f'Illegal registered standard action: {action}')
        context = self._action_context(actor)
        try:
            plan = module.plan(context, action)
        except ValueError as exc:
            raise IllegalAction(str(exc)) from exc
        # Validate the whole transaction before spending its action/resources.
        if (not isinstance(plan, ActionPlan) or plan.action_kind != action.kind
                or type(plan.focus_cost) is not int
                or plan.focus_cost != action.focus
                or not 0 <= plan.focus_cost <= 5 * context.rank
                or type(plan.minimum_focus_remaining) is not int
                or plan.minimum_focus_remaining < 0
                or plan.focus_cost == 0 and plan.minimum_focus_remaining != 0
                or plan.focus_cost > 0 and plan.minimum_focus_remaining < 1
                or not valid_references(plan.cost_rules)
                or plan.focus_cost > 0 and
                context.focus - plan.focus_cost < plan.minimum_focus_remaining):
            raise IllegalAction('Invalid registered action cost plan')
        if (not isinstance(plan.effects, tuple) or len(plan.effects) != 1
                or any(not self._valid_effect(effect) for effect in plan.effects)):
            raise IllegalAction('Unsupported or invalid registered effect plan')
        if ((isinstance(plan.effects[0], RestoreHealth) and plan.focus_cost == 0)
                or (isinstance(plan.effects[0], ActivateState) and plan.focus_cost != 0)):
            raise IllegalAction('Cost/effect combination has no validated action family')
        fighter = self.fighters[actor]
        fighter.standard_available = False
        before = fighter.focus
        fighter.focus -= plan.focus_cost
        fighter.focus_spent += plan.focus_cost
        if plan.focus_cost:
            self._record('focus_spent', plan.cost_rules, actor=fighter.profile.name,
                         amount=plan.focus_cost, focus_before=before,
                         focus_after=fighter.focus)
        for effect in plan.effects:
            if isinstance(effect, RestoreHealth):
                self._heal(actor, effect.amount, effect.rule)
            else:
                self._activate_state(actor, effect)

    @staticmethod
    def _valid_effect(effect) -> bool:
        if isinstance(effect, RestoreHealth):
            return (type(effect.amount) is int and effect.amount >= 0
                    and isinstance(effect.rule, str) and bool(effect.rule.strip()))
        if isinstance(effect, ActivateState):
            return (isinstance(effect.state, CombatState)
                    and valid_references(effect.rules))
        return False

    def _activate_state(self, actor: int, effect: ActivateState) -> None:
        fighter = self.fighters[actor]
        bindings = {
            CombatState.ATTACK_STANCE: ('stance', {'active': True}),
            CombatState.SHIELD: ('shield_activate', {'cost': 'standard'}),
            CombatState.DODGE: ('dodge', {'active_until_next_turn': True}),
        }
        event_type, data = bindings[effect.state]
        setattr(fighter, effect.state.value, True)
        self._record(event_type, effect.rules, actor=fighter.profile.name, **data)
