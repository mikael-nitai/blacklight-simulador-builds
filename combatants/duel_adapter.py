"""Coverage gate from full sheet data to the existing physical-duel engine.

The generic sheet retains every feature. This adapter accepts only mechanics
implemented for a direct open-field physical duel; unknown features block it.
"""

from dataclasses import dataclass

from blacklight.engine import Profile
from blacklight.rulesets import CURRENT_RULESET, LEGACY_RULESET
from .sheets import CharacterSheet


@dataclass(frozen=True)
class Mechanic:
    kind: str
    id: str
    max_level: int
    status: str
    explanation: str


REGISTRY = {
    (kind, identity): Mechanic(kind, identity, maximum, status, explanation)
    for kind, identity, maximum, status, explanation in (
        *(('power', name, 1, 'implemented', 'Physical duel action/passive')
          for name in ('healing_factor', 'brawling', 'fast_strikes',
                       'attack_stance', 'riposte', 'do_this_all_day',
                       'blazing_fast_fists')),
        ('power', 'mighty', 3, 'implemented', 'Level becomes Melee damage bonus'),
        ('power', 'sturdy', 3, 'implemented', 'Level becomes Health DR'),
        ('power', 'accuracy', 3, 'implemented', 'Level becomes Agility damage bonus'),
        ('power', 'disguise', 1, 'contextual', 'No disguise/deception phase in this direct duel'),
        *(('trait', name, 1, 'implemented', 'Initiative/reaction/check resource trait')
          for name in ('battle_ready', 'combat_reflexes', 'situational_awareness',
                       'signature_fast_strikes')),
        ('trait', 'weird', 1, 'contextual', 'No social phase in this direct duel'),
        ('trait', 'connections_military', 1, 'contextual', 'No contacts/reinforcements in this direct duel'),
        ('tag', 'heroic', 1, 'implemented', 'Nonlethal damage floor; Karma spending remains outside scope'),
        *(('tag', name, 1, 'contextual', 'No narrative phase in this direct duel')
          for name in ('obligation', 'rich', 'signature_weapon')),
        *(('house_weapon', name, 1, 'implemented', 'User-confirmed Rank 3 biological weapon')
          for name in ('blade', 'claw', 'hammer', 'shield')),
        ('equipment', 'ranged_attack', 1, 'implemented', 'Basic ranged attack with explicit range/ammunition'),
    )
}


class CoverageError(ValueError):
    def __init__(self, issues: list[str]):
        self.issues = issues
        super().__init__("Sheet cannot enter this engine: " + "; ".join(issues))


def coverage(sheet: CharacterSheet) -> dict:
    blockers = []
    rows = []
    if sheet.ruleset not in (LEGACY_RULESET, CURRENT_RULESET):
        blockers.append(f"ruleset {sheet.ruleset!r} is not implemented by the physical-duel adapters")
    if sheet.level('fast_strikes') and sheet.abilities['melee'] % 2:
        blockers.append('Fast Strikes with odd Melee damage bonus needs a table rounding ruling')
    if sheet.level('healing_factor') and sheet.abilities['resilience'] < 0:
        blockers.append('Healing Factor with negative Resilience is unresolved; do not interpret healing as damage')
    for feature in sheet.features:
        mechanic = REGISTRY.get((feature.kind, feature.id))
        status = mechanic.status if mechanic else 'pending'
        detail = mechanic.explanation if mechanic else 'No mechanic implementation registered'
        if mechanic is None or feature.level > mechanic.max_level:
            blockers.append(f"{feature.kind}:{feature.id} level {feature.level}: unsupported")
            status = 'pending'
        if feature.parameters and (feature.kind, feature.id) != ('equipment', 'ranged_attack'):
            blockers.append(f"{feature.kind}:{feature.id}: parameter variation has no adapter")
            status = 'pending'
        if feature.kind == 'equipment' and feature.id == 'ranged_attack':
            params = feature.parameters
            if (set(params) != {'range', 'ammunition'} or
                    type(params.get('range')) is not int or params.get('range', 0) < 1 or
                    type(params.get('ammunition')) is not bool):
                blockers.append('ranged_attack requires positive integer range and boolean ammunition')
                status = 'pending'
        if feature.kind == 'house_weapon' and feature.id == 'shield' and sheet.rank >= 4:
            blockers.append('Rank 4+ Shield reflection/progression is not implemented')
            status = 'pending'
        if feature.kind == 'house_weapon' and feature.id == 'blade' and sheet.rank < 2:
            blockers.append('Biological Blade requires Rank 2 in the confirmed table rule')
            status = 'pending'
        rows.append({'kind': feature.kind, 'id': feature.id, 'level': feature.level,
                     'status': status, 'detail': detail, 'sources': list(feature.sources)})
    for ability in ('melee', 'agility'):
        if sheet.defenses[ability] != 10 + sheet.abilities[ability]:
            blockers.append(f"Modified {ability} defense needs a new engine adapter")
    # The current physical engine has no actions that use these movement modes.
    unsupported_modes = set(sheet.movement) - {'run', 'climb', 'swim'}
    if unsupported_modes:
        blockers.append(f"Unsupported movement modes: {sorted(unsupported_modes)}")
    return {'sheet_id': sheet.id, 'revision': sheet.revision,
            'engine': ('split_fast_physical_duel' if sheet.ruleset == CURRENT_RULESET
                       else 'restricted_physical_duel_pool_v2'),
            'build_legality': 'not_certified_by_this_mechanics_adapter',
            'ready_for_this_scope': not blockers, 'blockers': blockers,
            'features': rows,
            'scope_limits': ['two actors', 'direct physical combat', 'open field',
                             'no Karma spending', 'no numeric limb penalties',
                             'no Focus attacks', 'no climbing/swimming phase']}


def compile_duel(sheet: CharacterSheet) -> Profile:
    report = coverage(sheet)
    if report['blockers']:
        raise CoverageError(report['blockers'])
    powers = frozenset(f.id for f in sheet.features if f.kind == 'power'
                       and REGISTRY[(f.kind, f.id)].status == 'implemented')
    traits = frozenset(f.id for f in sheet.features if f.kind == 'trait'
                       and REGISTRY[(f.kind, f.id)].status == 'implemented')
    weapons = frozenset(f.id for f in sheet.features if f.kind == 'house_weapon')
    ranged = next((f.parameters for f in sheet.features
                   if f.kind == 'equipment' and f.id == 'ranged_attack'), {})
    return Profile(
        sheet.name, sheet.rank, sheet.resources['health'], sheet.resources['focus'],
        sheet.abilities['melee'], sheet.abilities['agility'],
        sheet.abilities['resilience'], sheet.abilities['vigilance'],
        sheet.defenses['melee'], sheet.defenses['agility'], sheet.movement['run'],
        health_dr=sheet.level('sturdy'), melee_bonus=sheet.level('mighty'),
        ranged_bonus=sheet.level('accuracy'), ranged_range=ranged.get('range', 0),
        ranged_is_ammunition=ranged.get('ammunition', False),
        logic=sheet.abilities['logic'], initiative_modifier=sheet.initiative_modifier,
        run_speed_exception=sheet.movement['run'] != 5 + max(0, sheet.abilities['agility'] // 5),
        powers=powers, traits=traits, weapons=weapons,
        heroic=bool(sheet.level('heroic', 'tag')),
    )
