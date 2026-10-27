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
from .duel_adapter import compile_duel, coverage
from .modular_duel import ModularDuel
from .sheets import CharacterSheet, sheet_record


def _outcome(result, hero_name: str) -> str:
    return (result.outcome if result.outcome in ('draw', 'inconclusive')
            else 'win' if result.winner == hero_name else 'loss')


def _engine_metadata() -> dict:
    return {'execution_adapter': 'modular_physical_duel_v3',
            'lifecycle_scope': 'Dodge and Stunned expiry at turn start; immutable timing plans',
            'runtime': {'python': sys.version, 'implementation': sys.implementation.name,
                        'combat_core_dependencies': 'Python standard library',
                        'external_policy_dependency_scope':
                            'Class source is hashed; transitive external dependencies need a separate manifest'},
            'registered_action_modules': [
                {**asdict(module), 'family': type(module).__name__,
                 'requirements': [{'kind': item.kind, 'id': item.id}
                                  for item in module.requirements]}
                for module in DEFAULT_ACTIONS.modules.values()]}


def _source_manifest(policies: tuple[object, object]) -> dict[str, str]:
    sources = source_hashes()
    for path in sorted((ROOT / 'combatants').glob('*.py')):
        sources[str(path.relative_to(ROOT))] = sha256(path.read_bytes()).hexdigest()
    for policy in policies:
        source = inspect.getsourcefile(type(policy))
        if source is None or not Path(source).is_file():
            raise ValueError('Policy source file is unavailable for reproducible execution')
        path = Path(source).resolve()
        key = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        sources[key] = sha256(path.read_bytes()).hexdigest()
    return sources


def _assert_sources_unchanged(sources: dict[str, str], policies: tuple[object, object]) -> None:
    if sources != _source_manifest(policies):
        raise RuntimeError('Simulation sources changed during execution; result is not publishable')


def run_duel(hero: CharacterSheet, opponent: CharacterSheet,
             hero_policy: object, opponent_policy: object, *, seed: int,
             initial_distance: int = 1, max_rounds: int = 30) -> dict:
    profiles = (compile_duel(hero), compile_duel(opponent))
    policies = (hero_policy, opponent_policy)
    sources = _source_manifest(policies)
    if profiles[0].name == profiles[1].name:
        raise ValueError("Combatants need distinct display names for the audit ledger")
    result = ModularDuel(profiles, (hero_policy, opponent_policy), seed=seed,
                  initial_distance=initial_distance, max_rounds=max_rounds,
                  audit=True, action_registry=DEFAULT_ACTIONS).run()
    issues = audit_log(result.log,
                       {p.name: p.max_health for p in profiles},
                       {p.name: p.max_focus for p in profiles})
    if issues:
        raise RuntimeError(f"Generic character duel failed audit: {issues}")
    _assert_sources_unchanged(sources, policies)
    return {'schema': 'blacklight-generic-character-duel-v1',
            'damage_model': 'literal_marvel_pool_v2',
            'engine_version': __version__, 'seed': seed,
            **_engine_metadata(),
            'source_sha256': sources,
            'initial_distance': initial_distance, 'max_rounds': max_rounds,
            'sheets': [sheet_record(hero), sheet_record(opponent)],
            'policies': [asdict(hero_policy), asdict(opponent_policy)],
            'hero_id': hero.id, 'hero_revision': hero.revision,
            'opponent_id': opponent.id, 'opponent_revision': opponent.revision,
            'hero_outcome': _outcome(result, profiles[0].name),
            'coverage': [coverage(hero), coverage(opponent)],
            'result': asdict(result), 'audit_issues': issues}


def run_batch(hero: CharacterSheet, opponent: CharacterSheet,
              hero_policy: object, opponent_policy: object, *, n: int,
              master_seed: int, initial_distance: int = 1,
              max_rounds: int = 30, audit_every: int = 100) -> dict:
    if n < 1 or audit_every < 1:
        raise ValueError('Positive sample count and audit interval required')
    profiles = (compile_duel(hero), compile_duel(opponent))
    policies = (hero_policy, opponent_policy)
    sources = _source_manifest(policies)
    if profiles[0].name == profiles[1].name:
        raise ValueError('Combatants need distinct display names')
    cell = {'sheets': [sheet_record(hero), sheet_record(opponent)],
            'policies': [asdict(hero_policy), asdict(opponent_policy)],
            'initial_distance': initial_distance, 'max_rounds': max_rounds}
    cell_hash = sha256(json.dumps(cell, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    outcomes = dict.fromkeys(('win', 'loss', 'draw', 'inconclusive'), 0)
    moments = {name: Moment() for name in ('rounds', 'hero_final_health',
                                         'hero_final_focus', 'hero_damage_dealt',
                                         'hero_damage_taken')}
    audited = []
    for index in range(n):
        key = f'character-batch-v1|{master_seed}|{cell_hash}|{index}'
        seed = int.from_bytes(sha256(key.encode()).digest()[:8], 'big')
        audit_this = index % audit_every == 0
        result = ModularDuel(profiles, (hero_policy, opponent_policy), seed=seed,
                      initial_distance=initial_distance, max_rounds=max_rounds,
                      audit=audit_this, action_registry=DEFAULT_ACTIONS).run()
        if audit_this:
            issues = audit_log(result.log,
                               {p.name: p.max_health for p in profiles},
                               {p.name: p.max_focus for p in profiles})
            if issues:
                raise RuntimeError(f'Batch trace {index} failed audit: {issues}')
            audited.append({'index': index, 'seed': seed, 'issues': []})
        outcomes[_outcome(result, profiles[0].name)] += 1
        for name, value in (
            ('rounds', result.rounds), ('hero_final_health', result.final_health[0]),
            ('hero_final_focus', result.final_focus[0]),
            ('hero_damage_dealt', result.metrics[0]['damage_dealt']),
            ('hero_damage_taken', result.metrics[0]['damage_taken']),
        ):
            moments[name].add(value)
    _assert_sources_unchanged(sources, policies)
    return {'schema': 'blacklight-generic-character-batch-v1',
            'damage_model': 'literal_marvel_pool_v2', 'engine_version': __version__,
            **_engine_metadata(),
            'source_sha256': sources,
            **cell, 'n': n, 'master_seed': master_seed, 'cell_sha256': cell_hash,
            'seed_formula': 'first 8 SHA-256 bytes of character-batch-v1|master_seed|cell_sha256|index',
            'pairing_note': 'Seeds identify this cell; different cells are not assumed to be paired samples',
            'coverage': [coverage(hero), coverage(opponent)],
            'outcomes': outcomes,
            'rates': {name: {'estimate': count / n, 'wilson95': wilson(count, n)}
                      for name, count in outcomes.items()},
            'metrics_all_starts': {name: moment.summary() for name, moment in moments.items()},
            'audited_traces': audited}
