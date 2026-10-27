"""One full audited duel from two arbitrary versioned character sheets."""

from dataclasses import asdict
from hashlib import sha256
import inspect
import json
from pathlib import Path
import sys

from blacklight import __version__
from blacklight.audit import audit_log
from blacklight.experiment import ROOT, Moment, source_hashes, wilson
from .actions import DEFAULT_ACTIONS
from .battlefields import CorridorMap
from .duel_adapter import CURRENT_RULESET, LEGACY_RULESET, compile_duel, coverage
from .modular_duel import ModularDuel
from .split_fast import SplitFastDuel
from .sheets import CharacterSheet, sheet_record


def _outcome(result, hero_name: str) -> str:
    return (result.outcome if result.outcome in ('draw', 'inconclusive')
            else 'win' if result.winner == hero_name else 'loss')


def _engine_metadata(ruleset: str = LEGACY_RULESET, battlefield: CorridorMap | None = None) -> dict:
    current = ruleset == CURRENT_RULESET
    adapter = ('split_fast_corridor_v1' if current else 'modular_corridor_v1') if battlefield else (
        'split_fast_physical_duel_v1' if current else 'modular_physical_duel_v3')
    return {'execution_adapter': adapter,
            'table_ruleset': ruleset,
            'fast_zero_dice_bonus': current,
            'fast_strikes_contract': ('two checks before effects; one preselected effect limb; '
                                      'Shield before damage; both effects before Riposte'
                                      if current else 'historical single check, both weapon effects'),
            'lifecycle_scope': 'Dodge and Stunned expiry at turn start; immutable timing plans',
            'runtime': {'python': sys.version, 'implementation': sys.implementation.name,
                        'combat_core_dependencies': 'Python standard library',
                        'external_policy_dependency_scope':
                            'Class source is hashed; transitive external dependencies need a separate manifest'},
            'registered_action_modules': [
                {**asdict(module), 'family': type(module).__name__,
                 'requirements': [{'kind': item.kind, 'id': item.id}
                                  for item in module.requirements]}
                for module in DEFAULT_ACTIONS.modules.values()],
            **({'battlefield_scope': 'One-row corridor; no cover, collisions or knockback'}
               if battlefield else {})}


def _engine_for(hero: CharacterSheet, opponent: CharacterSheet, battlefield: CorridorMap | None = None):
    if hero.ruleset != opponent.ruleset:
        raise ValueError('Both combatants must declare the same table ruleset revision')
    if battlefield is not None:
        from experimental.corridor import CorridorDuel, SplitFastCorridorDuel
        return SplitFastCorridorDuel if hero.ruleset == CURRENT_RULESET else CorridorDuel
    return SplitFastDuel if hero.ruleset == CURRENT_RULESET else ModularDuel


def _battlefield_options(initial_distance: int | None, battlefield: CorridorMap | None) -> tuple[int, dict]:
    if battlefield is not None and not isinstance(battlefield, CorridorMap):
        raise ValueError('Unsupported battlefield; provide a validated CorridorMap or no map')
    distance = (battlefield.distance if battlefield else 1) if initial_distance is None else initial_distance
    if type(distance) is not int or distance < 1:
        raise ValueError('Initial distance must be a positive integer')
    if battlefield:
        if distance != battlefield.distance:
            raise ValueError('Initial distance conflicts with the map positions')
        return distance, {'length': battlefield.length, 'initial_positions': battlefield.initial_positions}
    return distance, {'initial_distance': distance}


def _policy_types(policies: tuple[object, object]) -> list[dict]:
    return [{'module': type(policy).__module__, 'class': type(policy).__qualname__}
            for policy in policies]


def _spatial_result(battle) -> dict:
    return {'final_positions': list(battle.positions), 'wall_reached': battle.wall_reached,
            'contact_occurred': battle.contact_occurred}


def _coverage_for(sheet: CharacterSheet, battlefield: CorridorMap | None) -> dict:
    report = coverage(sheet)
    if battlefield:
        report['character_mechanics_adapter'] = report['engine']
        report['engine'] = ('split_fast_corridor_v1' if sheet.ruleset == CURRENT_RULESET
                            else 'modular_corridor_v1')
        report['scope_limits'] = [item for item in report['scope_limits'] if item != 'open field']
        report['scope_limits'].append('one-dimensional corridor; no cover, collision or knockback')
    return report


def _audit_battle(result, profiles, battle, battlefield) -> list[str]:
    issues = audit_log(result.log, {p.name: p.max_health for p in profiles},
                        {p.name: p.max_focus for p in profiles})
    if battlefield:
        from experimental.corridor_audit import audit_corridor
        issues.extend(audit_corridor(
            result.log, tuple(p.name for p in profiles),
            initial_positions=battlefield.initial_positions, length=battlefield.length,
            final_positions=tuple(battle.positions), wall_reached=battle.wall_reached,
            contact_occurred=battle.contact_occurred))
    return issues


def _source_manifest(policies: tuple[object, object], battlefield: CorridorMap | None = None) -> dict[str, str]:
    sources = source_hashes()
    for path in sorted((ROOT / 'combatants').glob('*.py')):
        sources[str(path.relative_to(ROOT))] = sha256(path.read_bytes()).hexdigest()
    if battlefield:
        for name in ('experimental/__init__.py', 'experimental/corridor.py', 'experimental/corridor_audit.py',
                     'CORRIDOR_SPEC.md', 'CURRENT_CORRIDOR.md'):
            path = ROOT / name
            sources[str(path.relative_to(ROOT))] = sha256(path.read_bytes()).hexdigest()
    for policy in policies:
        source = inspect.getsourcefile(type(policy))
        if source is None or not Path(source).is_file():
            raise ValueError('Policy source file is unavailable for reproducible execution')
        path = Path(source).resolve()
        key = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        sources[key] = sha256(path.read_bytes()).hexdigest()
    return sources


def _assert_sources_unchanged(sources: dict[str, str], policies: tuple[object, object],
                              battlefield: CorridorMap | None = None) -> None:
    if sources != _source_manifest(policies, battlefield):
        raise RuntimeError('Simulation sources changed during execution; result is not publishable')


def run_duel(hero: CharacterSheet, opponent: CharacterSheet,
             hero_policy: object, opponent_policy: object, *, seed: int,
             initial_distance: int | None = None, max_rounds: int = 30,
             battlefield: CorridorMap | None = None) -> dict:
    initial_distance, options = _battlefield_options(initial_distance, battlefield)
    engine = _engine_for(hero, opponent, battlefield)
    profiles = (compile_duel(hero), compile_duel(opponent))
    policies = (hero_policy, opponent_policy)
    sources = _source_manifest(policies, battlefield)
    if profiles[0].name == profiles[1].name:
        raise ValueError("Combatants need distinct display names for the audit ledger")
    battle = engine(profiles, policies, seed=seed, max_rounds=max_rounds,
                     audit=True, action_registry=DEFAULT_ACTIONS, **options)
    result = battle.run()
    issues = _audit_battle(result, profiles, battle, battlefield)
    if issues:
        raise RuntimeError(f"Generic character duel failed audit: {issues}")
    _assert_sources_unchanged(sources, policies, battlefield)
    return {'schema': 'blacklight-generic-character-duel-v1',
            'damage_model': 'literal_marvel_pool_v2',
            'engine_version': __version__, 'seed': seed,
            **_engine_metadata(hero.ruleset, battlefield),
            'source_sha256': sources,
            'initial_distance': initial_distance, 'max_rounds': max_rounds,
            'sheets': [sheet_record(hero), sheet_record(opponent)],
            'policies': [asdict(hero_policy), asdict(opponent_policy)],
            'policy_types': _policy_types(policies),
            'hero_id': hero.id, 'hero_revision': hero.revision,
            'opponent_id': opponent.id, 'opponent_revision': opponent.revision,
            'hero_outcome': _outcome(result, profiles[0].name),
            'coverage': [_coverage_for(hero, battlefield), _coverage_for(opponent, battlefield)],
            'result': asdict(result), 'audit_issues': issues,
            **({'battlefield': battlefield.record(), 'battlefield_result': _spatial_result(battle)}
               if battlefield else {})}


def run_batch(hero: CharacterSheet, opponent: CharacterSheet,
              hero_policy: object, opponent_policy: object, *, n: int,
              master_seed: int, initial_distance: int | None = None,
              max_rounds: int = 30, audit_every: int = 100,
              battlefield: CorridorMap | None = None) -> dict:
    if n < 1 or audit_every < 1:
        raise ValueError('Positive sample count and audit interval required')
    initial_distance, options = _battlefield_options(initial_distance, battlefield)
    engine = _engine_for(hero, opponent, battlefield)
    profiles = (compile_duel(hero), compile_duel(opponent))
    policies = (hero_policy, opponent_policy)
    sources = _source_manifest(policies, battlefield)
    if profiles[0].name == profiles[1].name:
        raise ValueError('Combatants need distinct display names')
    cell = {'sheets': [sheet_record(hero), sheet_record(opponent)],
            'policies': [asdict(hero_policy), asdict(opponent_policy)],
            'initial_distance': initial_distance, 'max_rounds': max_rounds}
    if battlefield:
        cell['battlefield'] = battlefield.record()
    seed_version = 'character-batch-v2' if hero.ruleset == CURRENT_RULESET else 'character-batch-v1'
    if seed_version == 'character-batch-v2':
        cell['policy_types'] = _policy_types(policies)
    cell_hash = sha256(json.dumps(cell, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    outcomes = dict.fromkeys(('win', 'loss', 'draw', 'inconclusive'), 0)
    moments = {name: Moment() for name in ('rounds', 'hero_final_health',
                                         'hero_final_focus', 'hero_damage_dealt',
                                         'hero_damage_taken')}
    audited = []
    spatial_counts = {'wall_reached': 0, 'contact_occurred': 0}
    for index in range(n):
        key = f'{seed_version}|{master_seed}|{cell_hash}|{index}'
        seed = int.from_bytes(sha256(key.encode()).digest()[:8], 'big')
        audit_this = index % audit_every == 0
        battle = engine(profiles, policies, seed=seed, max_rounds=max_rounds,
                         audit=audit_this, action_registry=DEFAULT_ACTIONS, **options)
        result = battle.run()
        if audit_this:
            issues = _audit_battle(result, profiles, battle, battlefield)
            if issues:
                raise RuntimeError(f'Batch trace {index} failed audit: {issues}')
            audited.append({'index': index, 'seed': seed, 'issues': []})
        if battlefield:
            spatial_counts['wall_reached'] += battle.wall_reached
            spatial_counts['contact_occurred'] += battle.contact_occurred
        outcomes[_outcome(result, profiles[0].name)] += 1
        for name, value in (
            ('rounds', result.rounds), ('hero_final_health', result.final_health[0]),
            ('hero_final_focus', result.final_focus[0]),
            ('hero_damage_dealt', result.metrics[0]['damage_dealt']),
            ('hero_damage_taken', result.metrics[0]['damage_taken']),
        ):
            moments[name].add(value)
    _assert_sources_unchanged(sources, policies, battlefield)
    return {'schema': 'blacklight-generic-character-batch-v1',
            'damage_model': 'literal_marvel_pool_v2', 'engine_version': __version__,
            **_engine_metadata(hero.ruleset, battlefield),
            'source_sha256': sources,
            'policy_types': _policy_types(policies),
            **cell, 'n': n, 'master_seed': master_seed, 'cell_sha256': cell_hash,
            'seed_formula': f'first 8 SHA-256 bytes of {seed_version}|master_seed|cell_sha256|index',
            'pairing_note': 'Seeds identify this cell; different cells are not assumed to be paired samples',
            'coverage': [_coverage_for(hero, battlefield), _coverage_for(opponent, battlefield)],
            'outcomes': outcomes,
            'rates': {name: {'estimate': count / n, 'wilson95': wilson(count, n)}
                      for name, count in outcomes.items()},
            'metrics_all_starts': {name: moment.summary() for name, moment in moments.items()},
            'audited_traces': audited,
            **({'spatial_counts_all_starts': spatial_counts} if battlefield else {})}
