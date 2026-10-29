"""Versioned experimental correction for clearly weaponless close attacks."""

from blacklight.engine import IllegalAction
from .ram_prone_duel import RamProneDuel


class NonlethalRamProneDuel(RamProneDuel):
    """Default nonlethal for characters with no weapons or ranged equipment.

    Other non-Heroic bare attacks are blocked because this Profile does not tell
    us whether an accessible weapon is actually being carried. Declared lethal
    attacks are not supported here. The historical host is unchanged.
    """

    execution_scope = 'experimental_nonlethal_ram_prone_duel'

    def _allow_declared_armed_bare_attack(self, actor, target_actor, kind):
        """Subclasses may explicitly support a declared attack; default stays blocked."""
        return False

    def _attack(self, actor, kind, *, reaction=False, offhand=None, fast_strike=None,
                prepared_check=None, target_actor=None):
        target_actor = self._target_index(actor, target_actor)
        attacker, target = self.fighters[actor], self.fighters[target_actor]
        p, q = attacker.profile, target.profile
        bare = kind in ('melee', 'fast_strikes') and offhand is None
        if (bare and not p.heroic and (p.weapons or p.ranged_range)
                and not self._allow_declared_armed_bare_attack(actor, target_actor, kind)):
            raise IllegalAction('Default nonlethal status is unclear for an armed profile')
        eligible = bare and not p.heroic and not p.weapons and not p.ranged_range
        before = target.health
        result = super()._attack(actor, kind, reaction=reaction, offhand=offhand,
                                 fast_strike=fast_strike, prepared_check=prepared_check,
                                 target_actor=target_actor)
        if eligible and result.success and target.health <= -q.max_health:
            if not self.audit or not self.log:
                raise RuntimeError('The experimental nonlethal correction needs an attack trace')
            event = next((entry for entry in reversed(self.log) if entry.get('type') == 'attack'), None)
            if (event is None or event.get('actor') != p.name or event.get('target') != q.name
                    or event.get('mode') != kind or event.get('health_before') != before
                    or event.get('health_after') != target.health
                    or event.get('damage') != before - target.health):
                raise RuntimeError('Unable to associate the nonlethal limit with its attack')
            raw_after = target.health
            floor = -q.max_health + 1
            prevented = floor - raw_after
            if prevented < 1 or target.damage_taken < prevented or attacker.damage_dealt < prevented:
                raise RuntimeError('Nonlethal damage ledger cannot be reconciled')
            target.health = floor
            target.damage_taken -= prevented
            attacker.damage_dealt -= prevented
            event['health_after'] = floor
            event['damage'] = before - floor
            event['nonlethal_floor'] = floor
            event['nonlethal_raw_after'] = raw_after
            event['nonlethal_prevented'] = prevented
        return result
