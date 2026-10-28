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
from .runner import _assert_sources_unchanged, _policy_types, _source_manifest
from .sheets import CharacterSheet, sheet_record


GROUP_SCHEMA = 'blacklight-experimental-character-group-v1'


def run_group(sheets: tuple[CharacterSheet, ...], policies: tuple[GroupPolicy, ...], *,
              teams: tuple[str, ...], initiative_roles: tuple[str, ...],
              initiative_tie_order: tuple[int, ...] | None, seed: int,
              max_rounds: int = 30) -> dict:
    if (not isinstance(sheets, tuple) or len(sheets) < 2
            or any(not isinstance(sheet, CharacterSheet) for sheet in sheets)
            or not isinstance(policies, tuple) or len(policies) != len(sheets)
            or any(type(policy) is not GroupPolicy for policy in policies)
            or type(seed) is not int or type(max_rounds) is not int or max_rounds < 1):
        raise ValueError('Group needs versioned sheets, built-in GroupPolicy per participant and integer limits')
    if any(sheet.ruleset != CURRENT_RULESET for sheet in sheets):
        raise ValueError('Group supports only the current table ruleset')
    profiles = tuple(compile_duel(sheet) for sheet in sheets)
    for profile, policy in zip(profiles, policies):
        if 'healing_factor' in profile.powers and profile.resilience < 0:
            raise ValueError('Healing Factor with negative Resilience is unresolved in this group scope')
        if (policy.weapon != 'bare' and policy.weapon not in profile.weapons
                or policy.offhand is not None and policy.offhand not in profile.weapons
                or policy.weapon != 'bare' and policy.prefer_fast and 'fast_strikes' not in profile.powers
                or policy.shield_standard and 'shield' not in profile.weapons):
            raise ValueError(f'Policy requests an unsupported weapon or action for {profile.name}')
    sources = _source_manifest(policies)
    battle = GroupBattle(profiles, policies, teams=teams, initiative_roles=initiative_roles,
                         initiative_tie_order=initiative_tie_order, seed=seed,
                         max_rounds=max_rounds, audit=True, action_registry=DEFAULT_ACTIONS)
    result = battle.run()
    issues = (audit_profiled_log(result.log, profiles, ruleset=CURRENT_RULESET)
              + audit_group_initiative(result.log, profiles, initiative_roles, initiative_tie_order)
              + audit_group_trace(result, profiles, teams, seed=seed, max_rounds=max_rounds))
    if issues:
        raise RuntimeError(f'Experimental group trace failed available audits: {issues}')
    _assert_sources_unchanged(sources, policies)
    contract = {'schema': GROUP_SCHEMA, 'ruleset': CURRENT_RULESET,
                'execution_scope': 'experimental_group', 'sources': sources,
                'stunned_overlap': 'parallel_source_instances_unconfirmed',
                'reaction_order': 'queued_limb_order_with_nested_interrupts_interpretation'}
    contract_hash = sha256(json.dumps(contract, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    reports = []
    for sheet in sheets:
        report = coverage(sheet)
        report['character_mechanics_adapter'] = report['engine']
        report['engine'] = 'experimental_group_fixed_contact'
        report['scope_limits'] = [item for item in report['scope_limits']
                                  if item not in ('two actors', 'open field')]
        report['scope_limits'] += ['fixed mutual contact; no movement or knockback',
                                   'group combat and its audits are not certified']
        reports.append(report)
    return {'schema': GROUP_SCHEMA, 'table_ruleset': CURRENT_RULESET,
            'execution_scope': 'experimental_group', 'evidence_scope': 'experimental_group_uncertified',
            'engine_version': __version__, 'seed': seed, 'max_rounds': max_rounds,
            'runtime': {'python': sys.version, 'implementation': sys.implementation.name},
            'group_contract_sha256': contract_hash, 'group_contract': contract,
            'source_sha256': sources, 'sheets': [sheet_record(sheet) for sheet in sheets],
            'policies': [asdict(policy) for policy in policies], 'policy_types': _policy_types(policies),
            'policy_provenance': 'group_builtin_experimental',
            'teams': list(teams), 'initiative_roles': list(initiative_roles),
            'initiative_tie_order': list(initiative_tie_order) if initiative_tie_order else None,
            'coverage': reports, 'result': asdict(result), 'audit_issues': issues,
            'audit_scope': ['profiled physical arithmetic and ruleset', 'group initiative',
                            'group teams, Fast check inputs, partial reaction and result ledger'],
            'audit_limitations': ['does not certify every effect, action, reaction or turn transition',
                                  'overlapping Stunned duration and delayed reaction order are interpretations',
                                  'no group movement, knockback, Karma or Focus attacks',
                                  'build legality is not certified']}
