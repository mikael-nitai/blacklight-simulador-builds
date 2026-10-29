"""Explicit, incomplete adaptation of the visually transcribed Core profile."""

from dataclasses import dataclass, replace

from blacklight.engine import Profile

EXPECTED_ABILITIES = {
    'melee': (4, 14, 4), 'agility': (5, 15, 7), 'resilience': (3, 13, 3),
    'vigilance': (2, 12, 2), 'ego': (0, 10, 0), 'logic': (1, 11, 1),
}
EXPECTED_POWERS = {
    'Basic': ('Accuracy 2', 'Slow-Motion Dodge'),
    'Martial Arts': ('Banging Heads', 'Grappling Technique'),
    'Ranged Weapons': ('Dance of Death', 'Double Tap', 'Fast Hands', 'Point-Blank Parry',
                       'Slow-Motion Shoot-Dodge', 'Snap Shooting', 'Stopping Power', 'Weapons Blazing'),
}
EXPECTED_TRAITS = ('Battle Ready', 'Bloodthirsty', 'Combat Expert',
                   'Connections: Military (Hydra)', 'Determination', 'Piloting', 'Situational Awareness')
EXPECTED_TAGS = ('Backup', 'Public Identity', 'Villainous', 'Signature Weapon: Submachine Gun')


@dataclass(frozen=True)
class CrossbonesSubset:
    profile: Profile
    ranged_weapon: str
    included_powers: tuple[str, ...]
    omitted_powers: tuple[str, ...]
    included_traits: tuple[str, ...]
    omitted_traits: tuple[str, ...]
    omitted_tags: tuple[str, ...]
    assumptions: tuple[str, ...]


def build_crossbones_subset(evidence, *, accept_incomplete: bool) -> CrossbonesSubset:
    """Compile only the explicitly implemented portions, never the full character.

    In particular, a printed dash for damage reduction is interpreted as no
    damage reduction for this experiment; Karma and noncombat attributes are
    not used. This is not a character-sheet coverage adapter.
    """
    if accept_incomplete is not True:
        raise ValueError('The incomplete official-character subset must be explicit')
    if (not isinstance(evidence, dict)
            or evidence.get('schema') != 'blacklight.character-evidence.v1'
            or evidence.get('character') != 'Crossbones'
            or evidence.get('health_damage_reduction_printed') != '—'
            or evidence.get('initiative_printed') != '+2E'):
        raise ValueError('Unsupported Crossbones evidence record')
    ability = evidence['abilities']
    weapon = evidence['weapon_reference']
    source = evidence['source']
    expected_abilities = {name: {'score': score, 'defense': defense, 'noncombat': noncombat}
                          for name, (score, defense, noncombat) in EXPECTED_ABILITIES.items()}
    if (evidence.get('rank') != 3 or type(evidence['rank']) is not int
            or evidence.get('health') != 90 or type(evidence['health']) is not int
            or evidence.get('focus') != 90 or type(evidence['focus']) is not int
            or ability != expected_abilities or any(type(value) is not int
                for row in ability.values() for value in row.values())
            or evidence.get('movement') != {'run': 6, 'climb': 3, 'swim': 3, 'jump': 3}
            or any(type(value) is not int for value in evidence['movement'].values())
            or evidence.get('damage_printed') != {
                'melee': {'marvel_multiplier': 3, 'ability_bonus': 4},
                'agility': {'marvel_multiplier': 5, 'ability_bonus': 5},
                'ego': {'marvel_multiplier': 3, 'ability_bonus': 0},
                'logic': {'marvel_multiplier': 3, 'ability_bonus': 1}}
            or evidence.get('karma_printed') != '—' or evidence.get('focus_damage_reduction_printed') != '—'
            or evidence.get('powers') != {name: list(rows) for name, rows in EXPECTED_POWERS.items()}
            or evidence.get('traits') != list(EXPECTED_TRAITS) or evidence.get('tags') != list(EXPECTED_TAGS)
            or source.get('printed_page') != 155 or source.get('pdf_page') != 156
            or source.get('sha256') != 'ed5c2ba40910973d973fc06669bc361d3a30054753402299a180450977ca9bf6'):
        raise ValueError('Evidence differs from the verified printed profile')
    required = {'Accuracy 2', 'Slow-Motion Dodge', 'Double Tap'}
    powers = tuple(power for group in evidence['powers'].values() for power in group)
    traits = tuple(evidence['traits'])
    if (len(powers) != len(set(powers)) or not required.issubset(powers)
            or not {'Battle Ready', 'Situational Awareness'}.issubset(traits)
            or 'Heroic' in evidence['tags']
            or weapon.get('weapon') != 'Submachine Gun'
            or weapon.get('range_spaces') != 10 or weapon.get('damage_multiplier_bonus') != 1
            or weapon.get('close_range_trouble_max_spaces') != 5):
        raise ValueError('Required published facts are missing or inconsistent')
    profile = Profile(
        'Crossbones (recorte experimental)', evidence['rank'], evidence['health'], evidence['focus'],
        ability['melee']['score'], ability['agility']['score'], ability['resilience']['score'],
        ability['vigilance']['score'], ability['melee']['defense'], ability['agility']['defense'],
        evidence['movement']['run'], health_dr=0,
        ranged_bonus=max(2, weapon['damage_multiplier_bonus']), ranged_range=weapon['range_spaces'],
        ranged_is_ammunition=True, logic=ability['logic']['score'], initiative_modifier=2,
        powers=frozenset({'accuracy', 'slow_motion_dodge', 'double_tap'}),
        traits=frozenset({'battle_ready', 'situational_awareness'}), heroic=False,
    )
    included_traits = ('Battle Ready', 'Situational Awareness')
    return CrossbonesSubset(
        profile=profile, ranged_weapon='submachine_gun', included_powers=tuple(sorted(required)),
        omitted_powers=tuple(power for power in powers if power not in required),
        included_traits=included_traits,
        omitted_traits=tuple(trait for trait in traits if trait not in included_traits),
        omitted_tags=tuple(evidence['tags']),
        assumptions=('A printed Health DR dash is treated as zero for this experiment.',
                     'Karma, Focus attacks and noncombat abilities are not used.',
                     'Only single-target gunfire is modeled.',
                     'Table literal Marvel damage pools replace the printed Core damage formula.'),
    )


def build_crossbones_parry_subset(evidence, *, accept_incomplete: bool) -> CrossbonesSubset:
    """Versioned larger subset for ParryDuel; the earlier adapter stays intact."""
    base = build_crossbones_subset(evidence, accept_incomplete=accept_incomplete)
    promoted = {'Fast Hands', 'Point-Blank Parry'}
    if not promoted.issubset(base.omitted_powers):
        raise ValueError('The verified parry powers are missing')
    return replace(base,
        profile=replace(base.profile, powers=base.profile.powers | {'fast_hands', 'point_blank_parry'}),
        included_powers=tuple(sorted(set(base.included_powers) | promoted)),
        omitted_powers=tuple(power for power in base.omitted_powers if power not in promoted),
        assumptions=base.assumptions + ('The separate Fast Hands reaction can only pay a Ranged Weapons power.',
                                        'Point-Blank Parry does not target an unconscious attacker in this host.'))


def build_crossbones_stopping_subset(evidence, *, accept_incomplete: bool) -> CrossbonesSubset:
    """Larger experimental subset for StoppingDuel; previous versions remain stable."""
    base = build_crossbones_parry_subset(evidence, accept_incomplete=accept_incomplete)
    if 'Stopping Power' not in base.omitted_powers:
        raise ValueError('The verified Stopping Power is missing')
    return replace(base,
        profile=replace(base.profile, powers=base.profile.powers | {'stopping_power'}),
        included_powers=tuple(sorted(set(base.included_powers) | {'Stopping Power'})),
        omitted_powers=tuple(power for power in base.omitted_powers if power != 'Stopping Power'),
        assumptions=base.assumptions + ('Stopping Power does not follow up against an unconscious target in this host.',))
