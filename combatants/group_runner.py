"""Experimental, auditable fixed-contact encounters from versioned sheets.

This API produces exploratory records only. It does not use the certified duel
runner or assert that every group rule or character build has been validated.
"""

from dataclasses import asdict
from hashlib import sha256
import json
import sys

from blacklight import __version__
from blacklight.audit import audit_profiled_log
from .actions import DEFAULT_ACTIONS
from .duel_adapter import CURRENT_RULESET, compile_duel, coverage
from .group import GroupBattle, GroupPolicy
from .group_audit import audit_group_trace
from .group_initiative_audit import audit_group_initiative
from .group_lifecycle_audit import audit_group_lifecycle
from .group_grid import GroupGrid, GridGroupBattle, GridGroupPolicy
from .group_grid_audit import audit_group_grid
from .runner import _assert_sources_unchanged, _policy_types, _source_manifest
from .sheets import CharacterSheet, sheet_record


GROUP_SCHEMA = 'blacklight-experimental-character-group-v2'
GRID_SCHEMA = 'blacklight-experimental-character-group-grid-v1'


def run_group(sheets: tuple[CharacterSheet, ...], policies: tuple[GroupPolicy, ...], *,
              teams: tuple[str, ...], initiative_roles: tuple[str, ...],
              initiative_tie_order: tuple[int, ...] | None, seed: int,
              max_rounds: int = 30, grid: GroupGrid | None = None) -> dict:
    if grid is not None and not isinstance(grid, GroupGrid):
        raise ValueError('Unsupported experimental group grid')
    policy_class = GridGroupPolicy if grid is not None else GroupPolicy
    if (not isinstance(sheets, tuple) or len(sheets) < 2
            or any(not isinstance(sheet, CharacterSheet) for sheet in sheets)
            or not isinstance(policies, tuple) or len(policies) != len(sheets)
            or any(type(policy) is not policy_class for policy in policies)
            or type(seed) is not int or type(max_rounds) is not int or max_rounds < 1):
        raise ValueError('Group needs versioned sheets, matching built-in group policies and integer limits')
    if any(sheet.ruleset != CURRENT_RULESET for sheet in sheets):
        raise ValueError('Group supports only the current table ruleset')
    profiles = tuple(compile_duel(sheet) for sheet in sheets)
    for profile, policy in zip(profiles, policies):
        if (policy.weapon != 'bare' and policy.weapon not in profile.weapons
                or policy.offhand is not None and policy.offhand not in profile.weapons
                or policy.weapon != 'bare' and policy.prefer_fast and 'fast_strikes' not in profile.powers
                or policy.shield_standard and 'shield' not in profile.weapons):
            raise ValueError(f'Policy requests an unsupported weapon or action for {profile.name}')
    sources = _source_manifest(policies)
    engine = GridGroupBattle if grid is not None else GroupBattle
    battle = engine(profiles, policies, teams=teams, initiative_roles=initiative_roles,
                    initiative_tie_order=initiative_tie_order, seed=seed,
                    max_rounds=max_rounds, audit=True, action_registry=DEFAULT_ACTIONS,
                    **({'grid': grid} if grid is not None else {}))
    result = battle.run()
    issues = (audit_profiled_log(result.log, profiles, ruleset=CURRENT_RULESET)
              + audit_group_initiative(result.log, profiles, initiative_roles, initiative_tie_order)
              + audit_group_trace(result, profiles, teams, seed=seed, max_rounds=max_rounds)
              + audit_group_lifecycle(result.log, profiles))
    if grid is not None:
        issues.extend(audit_group_grid(result.log, profiles, width=grid.width, height=grid.height,
                                       initial_positions=grid.initial_positions,
                                       final_positions=result.final_positions))
    if issues:
        raise RuntimeError(f'Experimental group trace failed available audits: {issues}')
    _assert_sources_unchanged(sources, policies)
    schema = GRID_SCHEMA if grid is not None else GROUP_SCHEMA
    scope = 'experimental_group_grid' if grid is not None else 'experimental_group'
    contract = {'schema': schema, 'ruleset': CURRENT_RULESET,
                'execution_scope': scope, 'sources': sources,
                'stunned_overlap': 'parallel_source_instances_unconfirmed',
                'reaction_order': 'queued_limb_order_with_nested_interrupts_interpretation',
                **({'grid_restrictions': 'assumed ordinary Reach 1; one actor per cell; no occupied passage; '
                                         'ranged sight at most 200 spaces, only clear axis or 45-degree diagonal'}
                   if grid is not None else {})}
    contract_hash = sha256(json.dumps(contract, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    reports = []
    for sheet in sheets:
        report = coverage(sheet)
        report['character_mechanics_adapter'] = report['engine']
        report['engine'] = 'experimental_group_grid' if grid is not None else 'experimental_group_fixed_contact'
        report['scope_limits'] = [item for item in report['scope_limits']
                                  if item not in ('two actors', 'open field')]
        report['scope_limits'] += (['bounded open grid; limited sight; no knockback'] if grid is not None else
                                   ['fixed mutual contact; no movement or knockback']) + [
                                   'group combat and its audits are not certified']
        reports.append(report)
    return {'schema': schema, 'table_ruleset': CURRENT_RULESET,
            'execution_scope': scope, 'evidence_scope': 'experimental_group_uncertified',
            'engine_version': __version__, 'seed': seed, 'max_rounds': max_rounds,
            'runtime': {'python': sys.version, 'implementation': sys.implementation.name},
            'group_contract_sha256': contract_hash, 'group_contract': contract,
            'source_sha256': sources, 'sheets': [sheet_record(sheet) for sheet in sheets],
            'policies': [asdict(policy) for policy in policies], 'policy_types': _policy_types(policies),
            'policy_provenance': ('grid_group_builtin_experimental' if grid is not None
                                  else 'group_builtin_experimental'),
            'teams': list(teams), 'initiative_roles': list(initiative_roles),
            'initiative_tie_order': list(initiative_tie_order) if initiative_tie_order else None,
            'coverage': reports, 'result': asdict(result), 'audit_issues': issues,
            'audit_scope': ['profiled physical arithmetic and ruleset', 'group initiative',
                            'group teams, Fast check inputs, partial reaction and result ledger',
                            'group turn boundaries, Stunned/Dodge instances and reaction queue'] +
                           (['grid positions, movement, reach and constrained sight'] if grid is not None else []),
            'audit_limitations': ['does not certify every effect, action, reaction or turn transition',
                                  'overlapping Stunned duration and delayed reaction order are interpretations',
                                  ('no full sight, cover, difficult terrain, knockback, Karma or Focus attacks'
                                   if grid is not None else 'no group movement, knockback, Karma or Focus attacks'),
                                  *(['no standard-action or split movement; occupied cells cannot be traversed']
                                    if grid is not None else []),
                                  'build legality is not certified'],
            **({'grid': grid.record()} if grid is not None else {})}
