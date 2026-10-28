"""Experimental square-grid group host, limited to unambiguous sight lines.

One regular-sized actor per cell, no occupied-cell traversal, no obstacles,
no cover and no displacement powers. Those are scenario restrictions, not a
claim that the Core forbids every other configuration.
"""

from collections import deque
from dataclasses import dataclass, replace

from blacklight.engine import Action, IllegalAction
from .group import GroupBattle, GroupObservation, GroupPolicy, GroupResult, TargetAction
from .split_fast import FastAction, is_fast


def grid_distance(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def supported_sight(a, b, occupied):
    """Only straight horizontal, vertical and 45-degree clear lines are modeled."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = max(abs(dx), abs(dy))
    if length < 1 or length > 200 or dx and dy and abs(dx) != abs(dy):
        return False
    sx = (dx > 0) - (dx < 0)
    sy = (dy > 0) - (dy < 0)
    return all((a[0] + sx * n, a[1] + sy * n) not in occupied
               for n in range(1, length))


@dataclass(frozen=True)
class GroupGrid:
    width: int
    height: int
    initial_positions: tuple[tuple[int, int], ...]

    def __post_init__(self):
        if (type(self.width) is not int or type(self.height) is not int
                or self.width < 1 or self.height < 1 or self.width * self.height > 2500
                or not isinstance(self.initial_positions, tuple) or len(self.initial_positions) < 2
                or any(not isinstance(point, tuple) or len(point) != 2
                       or any(type(value) is not int for value in point)
                       or not (0 <= point[0] < self.width and 0 <= point[1] < self.height)
                       for point in self.initial_positions)
                or len(set(self.initial_positions)) != len(self.initial_positions)):
            raise ValueError('Invalid bounded grid or overlapping initial positions')

    def record(self):
        return {'width': self.width, 'height': self.height,
                'initial_positions': [list(point) for point in self.initial_positions]}


@dataclass(frozen=True)
class GridMove:
    path: tuple[tuple[int, int], ...] = ()

    def __post_init__(self):
        if (not isinstance(self.path, tuple)
                or any(not isinstance(point, tuple) or len(point) != 2
                       or any(type(value) is not int for value in point) for point in self.path)):
            raise ValueError('Grid path must contain integer coordinate tuples')


@dataclass(frozen=True)
class GridObservation(GroupObservation):
    width: int = 0
    height: int = 0
    positions: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True)
class GridGroupPolicy(GroupPolicy):
    """Simple approach-and-attack policy using only the visible grid snapshot."""

    def _can_attack(self, action, observation, target, position=None):
        origin = observation.positions[observation.actor] if position is None else position
        destination = observation.positions[target]
        distance = grid_distance(origin, destination)
        if action.kind == 'ranged':
            occupied = set(observation.positions)
            occupied.discard(observation.positions[observation.actor])
            occupied.add(origin)
            return (observation.me.ranged_range > 0 and distance <= 2 * observation.me.ranged_range
                    and supported_sight(origin, destination, occupied))
        return distance <= 1

    def choose_move(self, observation):
        start = observation.positions[observation.actor]
        occupied = set(observation.positions) - {start}
        queue = deque([(start, ())])
        paths = {start: ()}
        while queue:
            point, path = queue.popleft()
            if len(path) >= observation.me.run_speed:
                continue
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == dy == 0:
                        continue
                    nxt = (point[0] + dx, point[1] + dy)
                    if (0 <= nxt[0] < observation.width and 0 <= nxt[1] < observation.height
                            and nxt not in occupied and nxt not in paths):
                        paths[nxt] = path + (nxt,)
                        queue.append((nxt, paths[nxt]))
        enemies = observation.enemies
        if not enemies:
            return GridMove()
        attack = Action('ranged' if observation.me.ranged_range else 'melee')
        def objective(point):
            reachable = any(self._can_attack(attack, observation, target, point) for target in enemies)
            nearest = min(grid_distance(point, observation.positions[target]) for target in enemies)
            return (not reachable, len(paths[point]) if reachable else nearest,
                    len(paths[point]), point)
        return GridMove(paths[min(paths, key=objective)])

    def choose_post_move(self, observation):
        return GridMove()

    def choose_action(self, observation):
        action = super().choose_action(observation)
        # This first grid host supports the movement action, not converting the
        # standard action into a second movement action.
        return Action('wait') if action.kind == 'move' else action

    def _targeted(self, action, observation):
        if action.kind not in ('melee', 'ranged', 'fast_strikes', 'blade', 'blade_fast',
                               'claw', 'claw_fast', 'hammer', 'hammer_fast'):
            return action
        enemies = [i for i in observation.enemies if self._can_attack(action, observation, i)]
        if not enemies:
            return Action('wait')
        def key(index):
            fighter = observation.fighters[index]
            defense = (fighter.agility_defense if action.kind == 'ranged'
                       and 'brawling' not in fighter.powers else fighter.melee_defense)
            value = (defense if self.target_order == 'lowest_defense' else
                     -fighter.health if self.target_order == 'highest_health' else fighter.health)
            return value, index
        enemies.sort(key=key)
        if is_fast(action.kind):
            second = enemies[1] if self.split_targets and len(enemies) > 1 else enemies[0]
            return replace(action, targets=(enemies[0], second))
        return TargetAction(action.kind, target_actor=enemies[0])


@dataclass(frozen=True)
class GridGroupResult(GroupResult):
    final_positions: tuple[tuple[int, int], ...] = ()


class GridGroupBattle(GroupBattle):
    execution_scope = 'experimental_group_grid'

    def __init__(self, profiles, policies, *, grid: GroupGrid, **kwargs):
        if not isinstance(grid, GroupGrid) or len(grid.initial_positions) != len(profiles):
            raise ValueError('Grid must contain one position for each participant')
        super().__init__(profiles, policies, **kwargs)
        self.grid = grid
        self.positions = list(grid.initial_positions)

    def _assert_geometry(self):
        positions = self.positions
        if (len(positions) != len(self.fighters)
                or any(not isinstance(p, tuple) or len(p) != 2
                       or any(type(v) is not int for v in p)
                       or not (0 <= p[0] < self.grid.width and 0 <= p[1] < self.grid.height)
                       for p in positions) or len(set(positions)) != len(positions)
                or type(self.distance) is not int or self.distance != 1):
            raise RuntimeError('Group grid geometry is inconsistent')

    def _distance_between(self, actor, target_actor):
        self._assert_geometry()
        return grid_distance(self.positions[actor], self.positions[target_actor])

    def _target_index(self, actor, target_actor=None):
        if type(actor) is not int or not 0 <= actor < len(self.fighters):
            raise IllegalAction('Actor is outside the roster')
        if target_actor is None and hasattr(self, 'positions'):
            candidates = self._enemies(actor) or self._enemies(actor, conscious=False)
            target_actor = min(candidates, key=lambda i: (self._distance_between(actor, i),
                                                          self.fighters[i].health, i))
        return super()._target_index(actor, target_actor)

    def observe(self, actor, target_actor=None):
        basic = super().observe(actor, target_actor)
        return GridObservation(**vars(basic), width=self.grid.width, height=self.grid.height,
                               positions=tuple(self.positions))

    def _permitted_target(self, actor, target, kind):
        distance = self._distance_between(actor, target)
        if kind == 'ranged':
            reach = self.fighters[actor].profile.ranged_range
            return (reach > 0 and distance <= 2 * reach and
                    supported_sight(self.positions[actor], self.positions[target], set(self.positions)))
        return distance <= 1

    def _target_choices(self, actor, choices):
        choices = super()._target_choices(actor, choices)
        return tuple(action for action in choices if (
            all(self._permitted_target(actor, target, action.kind) for target in action.targets)
            if isinstance(action, FastAction) else
            self._permitted_target(actor, action.target_actor, action.kind)
            if isinstance(action, TargetAction) else True))

    def _fast_targets(self, actor, action):
        targets = super()._fast_targets(actor, action)
        if any(not self._permitted_target(actor, target, action.kind) for target in targets):
            raise IllegalAction('Each Fast limb must reach its own target')
        return targets

    def _attack_targets_available(self, actor):
        return any(self._distance_between(actor, target) <= 1 for target in self._enemies(actor))

    def _attack_check_spec(self, actor, kind, target_actor=None):
        target = self._target_index(actor, target_actor)
        if not self._permitted_target(actor, target, kind):
            raise IllegalAction('Target is outside supported range or sight')
        return super()._attack_check_spec(actor, kind, target)

    def _attack(self, actor, kind, **kwargs):
        target = self._target_index(actor, kwargs.get('target_actor'))
        if not self._permitted_target(actor, target, kind):
            raise IllegalAction('Target is outside supported range or sight')
        return super()._attack(actor, kind, **kwargs)

    def _move(self, actor, move, *, as_standard=False):
        self._assert_geometry()
        if (type(actor) is not int or not 0 <= actor < len(self.fighters)
                or not isinstance(move, GridMove) or type(as_standard) is not bool):
            raise IllegalAction('Grid movement requires an actor and declared path')
        fighter = self.fighters[actor]
        if (as_standard or self.active_actor != actor or not fighter.conscious
                or fighter.stunned_by is not None or not fighter.movement_available
                or len(move.path) > fighter.profile.run_speed):
            raise IllegalAction('Grid movement is unavailable or exceeds speed')
        origin = self.positions[actor]
        occupied = set(self.positions) - {origin}
        previous = origin
        for point in move.path:
            if (not 0 <= point[0] < self.grid.width or not 0 <= point[1] < self.grid.height
                    or point in occupied or grid_distance(previous, point) != 1):
                raise IllegalAction('Grid path crosses an occupied cell or leaves adjacent spaces')
            previous = point
        fighter.movement_available = False
        self.positions[actor] = previous
        self._record('group_grid_move', ('ACT-01', 'ACT-06', 'MAP-01'),
                     actor=fighter.profile.name, origin=list(origin),
                     path=[list(point) for point in move.path], destination=list(previous),
                     steps=len(move.path), as_standard=False)

    def _finish(self, outcome, winner, bonus_occurred):
        result = super()._finish(outcome, winner, bonus_occurred)
        return GridGroupResult(**vars(result), final_positions=tuple(self.positions))
