"""Small reusable action modules; definitions cannot mutate battle state.

This first family covers a standard self-heal paid with Focus. New mechanics
can register other action modules without adding character-name branches.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol

from blacklight.engine import Action


@dataclass(frozen=True)
class ActionContext:
    rank: int
    health: int
    max_health: int
    focus: int
    powers: frozenset[str]


@dataclass(frozen=True)
class RestoreHealth:
    amount: int
    rule: str


@dataclass(frozen=True)
class ActionPlan:
    action_kind: str
    focus_cost: int
    minimum_focus_remaining: int
    cost_rules: tuple[str, ...]
    effects: tuple[RestoreHealth, ...]


class ActionModule(Protocol):
    kind: str
    required_power: str
    sources: tuple[str, ...]

    def available(self, context: ActionContext) -> tuple[Action, ...]: ...
    def plan(self, context: ActionContext, request: Action) -> ActionPlan: ...


@dataclass(frozen=True)
class FocusSelfHeal:
    kind: str
    required_power: str
    minimum_spend: int
    maximum_spend_per_rank: int
    minimum_focus_remaining: int
    health_per_focus: int
    cost_rules: tuple[str, ...]
    healing_rule: str
    sources: tuple[str, ...]

    def __post_init__(self) -> None:
        values = (self.minimum_spend, self.maximum_spend_per_rank,
                  self.minimum_focus_remaining, self.health_per_focus)
        if (any(type(value) is not int or value < 1 for value in values)
                or not self.kind or not self.required_power or not self.sources):
            raise ValueError('Incomplete or invalid self-heal rule definition')

    def available(self, context: ActionContext) -> tuple[Action, ...]:
        if self.required_power not in context.powers:
            return ()
        maximum = min(self.maximum_spend_per_rank * context.rank,
                      context.focus - self.minimum_focus_remaining)
        return tuple(Action(self.kind, spent)
                     for spent in range(self.minimum_spend, maximum + 1))

    def plan(self, context: ActionContext, request: Action) -> ActionPlan:
        if request not in self.available(context):
            raise ValueError('Request is not permitted by this action module')
        return ActionPlan(
            self.kind, request.focus, self.minimum_focus_remaining,
            self.cost_rules,
            (RestoreHealth(self.health_per_focus * request.focus,
                           self.healing_rule),),
        )


DO_THIS_ALL_DAY = FocusSelfHeal(
    kind='heal', required_power='do_this_all_day', minimum_spend=5,
    maximum_spend_per_rank=5, minimum_focus_remaining=1,
    health_per_focus=2, cost_rules=('RES-01', 'POW-07'),
    healing_rule='POW-07', sources=('Core Rulebook p.94', 'RULES_AUDIT.md POW-07/RES-01'),
)


class ActionRegistry:
    def __init__(self, modules: tuple[ActionModule, ...]) -> None:
        definitions = {}
        for module in modules:
            if (not isinstance(module.kind, str) or not module.kind
                    or not isinstance(module.required_power, str) or not module.required_power):
                raise ValueError('Action module needs an identity and required power')
            if module.kind in definitions:
                raise ValueError(f'Duplicate action module: {module.kind}')
            if (not isinstance(module.sources, tuple) or not module.sources
                    or any(not isinstance(source, str) or not source for source in module.sources)):
                raise ValueError(f'Action module lacks a source: {module.kind}')
            definitions[module.kind] = module
        self.modules = MappingProxyType(definitions)

    def get(self, kind: str) -> ActionModule | None:
        return self.modules.get(kind)


DEFAULT_ACTIONS = ActionRegistry((DO_THIS_ALL_DAY,))
