"""Small reusable action modules receiving no mutable battle state.

Families currently cover Focus-paid self-healing and zero-cost state activation.
New definitions contain no character-name branches.
"""

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Protocol

from blacklight.engine import Action


def _text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def valid_references(value) -> bool:
    return isinstance(value, tuple) and bool(value) and all(_text(item) for item in value)


def valid_requirements(value) -> bool:
    return (isinstance(value, tuple)
            and all(isinstance(item, CapabilityRequirement) for item in value)
            and len(set(value)) == len(value))


@dataclass(frozen=True)
class CapabilityRequirement:
    kind: str
    id: str

    def __post_init__(self) -> None:
        if self.kind not in ('power', 'trait', 'weapon') or not _text(self.id):
            raise ValueError('Invalid capability requirement')


class CombatState(str, Enum):
    ATTACK_STANCE = 'stance'
    SHIELD = 'shield_active'
    DODGE = 'dodging'


@dataclass(frozen=True)
class ActionContext:
    rank: int
    health: int
    max_health: int
    focus: int
    powers: frozenset[str]
    traits: frozenset[str] = frozenset()
    weapons: frozenset[str] = frozenset()
    states: frozenset[CombatState] = frozenset()

    def meets(self, requirements: tuple[CapabilityRequirement, ...]) -> bool:
        available = {'power': self.powers, 'trait': self.traits, 'weapon': self.weapons}
        return all(requirement.id in available[requirement.kind]
                   for requirement in requirements)


@dataclass(frozen=True)
class RestoreHealth:
    amount: int
    rule: str


@dataclass(frozen=True)
class ActivateState:
    state: CombatState
    rules: tuple[str, ...]


@dataclass(frozen=True)
class ActionPlan:
    action_kind: str
    focus_cost: int
    minimum_focus_remaining: int
    cost_rules: tuple[str, ...]
    effects: tuple[RestoreHealth | ActivateState, ...]


class ActionModule(Protocol):
    kind: str
    requirements: tuple[CapabilityRequirement, ...]
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

    @property
    def requirements(self) -> tuple[CapabilityRequirement, ...]:
        return (CapabilityRequirement('power', self.required_power),)

    def __post_init__(self) -> None:
        values = (self.minimum_spend, self.maximum_spend_per_rank,
                  self.minimum_focus_remaining, self.health_per_focus)
        if (any(type(value) is not int or value < 1 for value in values)
                or not _text(self.kind) or not _text(self.required_power)
                or not valid_references(self.cost_rules) or not _text(self.healing_rule)
                or not valid_references(self.sources)):
            raise ValueError('Incomplete or invalid self-heal rule definition')

    def available(self, context: ActionContext) -> tuple[Action, ...]:
        if not context.meets(self.requirements):
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


@dataclass(frozen=True)
class StateActivation:
    kind: str
    requirements: tuple[CapabilityRequirement, ...]
    state: CombatState
    require_inactive: bool
    rules: tuple[str, ...]
    sources: tuple[str, ...]

    def __post_init__(self) -> None:
        if (not _text(self.kind) or not isinstance(self.state, CombatState)
                or type(self.require_inactive) is not bool
                or not valid_requirements(self.requirements)
                or not valid_references(self.rules) or not valid_references(self.sources)):
            raise ValueError('Invalid state-activation rule definition')

    def available(self, context: ActionContext) -> tuple[Action, ...]:
        if (not context.meets(self.requirements) or
                self.require_inactive and self.state in context.states):
            return ()
        return (Action(self.kind),)

    def plan(self, context: ActionContext, request: Action) -> ActionPlan:
        if request not in self.available(context):
            raise ValueError('Request is not permitted by this state module')
        return ActionPlan(self.kind, 0, 0, self.rules,
                          (ActivateState(self.state, self.rules),))


DO_THIS_ALL_DAY = FocusSelfHeal(
    kind='heal', required_power='do_this_all_day', minimum_spend=5,
    maximum_spend_per_rank=5, minimum_focus_remaining=1,
    health_per_focus=2, cost_rules=('RES-01', 'POW-07'),
    healing_rule='POW-07', sources=('Core Rulebook p.94', 'RULES_AUDIT.md POW-07/RES-01'),
)

ATTACK_STANCE = StateActivation(
    'stance', (CapabilityRequirement('power', 'attack_stance'),),
    CombatState.ATTACK_STANCE, True, ('POW-09',),
    ('Core Rulebook p.83', 'RULES_AUDIT.md POW-09'),
)
STANDARD_SHIELD = StateActivation(
    'shield', (CapabilityRequirement('weapon', 'shield'),),
    CombatState.SHIELD, True, ('HR-04',),
    ('User table ruling HR-04: standard-action activation',),
)
DODGE = StateActivation(
    'dodge', (), CombatState.DODGE, False, ('ACT-07',),
    ('Core Rulebook p.30', 'RULES_AUDIT.md ACT-07'),
)


class ActionRegistry:
    def __init__(self, modules: tuple[ActionModule, ...]) -> None:
        definitions = {}
        for module in modules:
            if not _text(module.kind):
                raise ValueError('Action module needs an identity')
            requirements = module.requirements
            if not valid_requirements(requirements):
                raise ValueError('Action module needs explicit typed capability requirements')
            if module.kind in definitions:
                raise ValueError(f'Duplicate action module: {module.kind}')
            if not valid_references(module.sources):
                raise ValueError(f'Action module lacks a source: {module.kind}')
            definitions[module.kind] = module
        self.modules = MappingProxyType(definitions)

    def get(self, kind: str) -> ActionModule | None:
        return self.modules.get(kind)


DEFAULT_ACTIONS = ActionRegistry((DO_THIS_ALL_DAY, ATTACK_STANCE, STANDARD_SHIELD, DODGE))
