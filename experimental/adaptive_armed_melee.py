"""Experimental declared lethal bare attacks and an adaptive ranged opponent."""

from dataclasses import dataclass

from blacklight.engine import Action, IllegalAction, Move
from .stopping_duel import StoppingPolicy
from .stopping_ram_duel import StoppingRamDuel


@dataclass(frozen=True)
class ShieldAwarePolicy(StoppingPolicy):
    """Approach a visible active shield; otherwise use the existing ranged policy."""

    def choose_move(self, observation):
        if observation.foe.shield_active:
            steps = min(observation.me.run_speed, max(0, observation.distance - 1))
            return self._prone_move(observation, Move('approach' if steps else 'stay', steps))
        return super().choose_move(observation)

    def choose_post_move(self, observation):
        return Move() if observation.foe.shield_active else super().choose_post_move(observation)

    def choose_action(self, observation):
        if not observation.foe.shield_active:
            return super().choose_action(observation)
        if self.treat_bleeding and observation.me.bleeding and 'healing_factor' not in observation.me.powers:
            return Action('treat_bleeding')
        if observation.distance <= 1:
            return Action('melee')
        steps = min(observation.me.run_speed, observation.distance - 1)
        if not steps:
            return Action('wait')
        move = self._prone_move(observation, Move('approach', steps))
        return Action('move', move=move) if move.steps else Action('wait')


class DeclaredArmedMeleeDuel(StoppingRamDuel):
    """Require an explicit per-actor lethal declaration, without changing old hosts."""

    execution_scope = 'experimental_declared_armed_melee_stopping_ram_duel'

    def __init__(self, *args, declared_armed_lethal, **kwargs):
        if (not isinstance(declared_armed_lethal, tuple)
                or any(not isinstance(name, str) or not name for name in declared_armed_lethal)
                or len(set(declared_armed_lethal)) != len(declared_armed_lethal)):
            raise ValueError('Declare distinct lethal melee actors explicitly')
        self.declared_armed_lethal = declared_armed_lethal
        super().__init__(*args, **kwargs)
        names = {f.profile.name: f.profile for f in self.fighters}
        if any(name not in names or names[name].heroic
               or not (names[name].weapons or names[name].ranged_range)
               for name in declared_armed_lethal):
            raise ValueError('Declared actor must be a non-Heroic armed profile')

    def _allow_declared_armed_bare_attack(self, actor, target_actor, kind):
        attacker = self.fighters[actor].profile.name
        if kind != 'melee' or attacker not in self.declared_armed_lethal:
            return False
        self._record('lethality_declaration', ('CORE-P36-LETHAL',), actor=attacker,
                     target=self.fighters[target_actor].profile.name, mode=kind, choice='lethal')
        return True

    def _attack(self, actor, kind, *, reaction=False, offhand=None, fast_strike=None,
                prepared_check=None, target_actor=None):
        target = self._target_index(actor, target_actor)
        profile = self.fighters[actor].profile
        marked = (kind == 'melee' and offhand is None and not profile.heroic
                  and bool(profile.weapons or profile.ranged_range)
                  and profile.name in self.declared_armed_lethal)
        if marked and prepared_check is not None:
            raise IllegalAction('Lethality must be declared before an attack check')
        start = len(self.log)
        result = super()._attack(actor, kind, reaction=reaction, offhand=offhand,
                                 fast_strike=fast_strike, prepared_check=prepared_check,
                                 target_actor=target)
        if marked:
            attacks = [e for e in self.log[start:] if e.get('type') == 'attack'
                       and e.get('actor') == profile.name and e.get('target') == self.fighters[target].profile.name]
            if len(attacks) != 1:
                raise RuntimeError('Declared lethal attack has no unique trace')
            attacks[0]['declared_lethality'] = 'lethal'
        return result
