"""Progressive action-module adapter around the validated physical Duel.

Only Focus-paid self-healing is migrated so far. Other mechanics keep using
the existing resolver and are explicitly listed as pending migrations.
"""

from blacklight.engine import Action, Duel, IllegalAction
from .actions import (ActionContext, ActionPlan, ActionRegistry, DEFAULT_ACTIONS,
                      RestoreHealth)


class ModularDuel(Duel):
    def __init__(self, *args, action_registry: ActionRegistry = DEFAULT_ACTIONS,
                 **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.action_registry = action_registry

    def _action_context(self, actor: int) -> ActionContext:
        fighter = self.fighters[actor]
        profile = fighter.profile
        return ActionContext(profile.rank, fighter.health, profile.max_health,
                             fighter.focus, profile.powers)

    @staticmethod
    def _module_actions(module, context: ActionContext) -> tuple[Action, ...]:
        requests = module.available(context)
        if (not isinstance(requests, tuple)
                or any(not isinstance(request, Action) or request.kind != module.kind
                       or type(request.focus) is not int
                       or not 0 <= request.focus <= 5 * context.rank
                       or context.focus - request.focus < 1
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
                if module.required_power in context.powers:
                    result.extend(self._module_actions(module, context))
                emitted.add(action.kind)
        for kind, module in self.action_registry.modules.items():
            if kind not in emitted:
                if module.required_power in context.powers:
                    result.extend(self._module_actions(module, context))
        return tuple(result)

    def _act(self, actor: int, action: Action) -> None:
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
                or plan.minimum_focus_remaining < 1
                or not isinstance(plan.cost_rules, tuple) or not plan.cost_rules
                or any(not isinstance(rule, str) or not rule for rule in plan.cost_rules)
                or context.focus - plan.focus_cost < plan.minimum_focus_remaining):
            raise IllegalAction('Invalid registered action cost plan')
        if (not isinstance(plan.effects, tuple) or not plan.effects
                or any(not isinstance(effect, RestoreHealth) or
                       type(effect.amount) is not int or effect.amount < 0
                       or not isinstance(effect.rule, str) or not effect.rule
                       for effect in plan.effects)):
            raise IllegalAction('Unsupported or invalid registered effect plan')
        fighter = self.fighters[actor]
        fighter.standard_available = False
        before = fighter.focus
        fighter.focus -= plan.focus_cost
        fighter.focus_spent += plan.focus_cost
        self._record('focus_spent', plan.cost_rules, actor=fighter.profile.name,
                     amount=plan.focus_cost, focus_before=before,
                     focus_after=fighter.focus)
        for effect in plan.effects:
            # Core healing helper retains effective-healing cap, Bleeding
            # removal and log order while this family is migrated.
            self._heal(actor, effect.amount, effect.rule)
