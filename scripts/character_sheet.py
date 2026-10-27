"""Inspect, import evidence, and run versioned character sheets."""

from argparse import ArgumentParser
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from blacklight.experiment import strategies
from blacklight.policies import ATTACK, KITER
from combatants import load_sheet, coverage
from combatants.pdf_draft import extract_draft
from combatants.runner import run_duel, run_batch
from combatants.duel_adapter import CURRENT_RULESET, LEGACY_RULESET
from combatants.split_fast import SplitFastPolicy
from combatants.battlefields import CorridorMap
from combatants.terrain_policies import WallAwarePolicy


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    validate = commands.add_parser('validate')
    validate.add_argument('sheet', type=Path)
    validate.add_argument('--output', type=Path)
    extract = commands.add_parser('extract-pdf')
    extract.add_argument('pdf', type=Path)
    extract.add_argument('--output', type=Path, required=True)
    for command in ('duel', 'batch'):
        sub = commands.add_parser(command)
        sub.add_argument('--hero', type=Path, required=True)
        sub.add_argument('--opponent', type=Path, required=True)
        sub.add_argument('--policy', default='attack')
        sub.add_argument('--opponent-policy', default='attack')
        sub.add_argument('--distance', type=int)
        sub.add_argument('--corridor-length', type=int)
        sub.add_argument('--positions', type=int, nargs=2)
        sub.add_argument('--wall-aware', action='store_true')
        sub.add_argument('--opponent-wall-aware', action='store_true')
        sub.add_argument('--output', type=Path, required=True)
        sub.add_argument('--effect-limb', type=int, choices=(0, 1), default=0,
                         help='For current Fast rules: limb0 is the primary, limb1 the offhand')
        sub.add_argument('--opponent-effect-limb', type=int, choices=(0, 1), default=0)
        sub.add_argument('--historical-rules', action='store_true',
                         help='Explicitly allow the preserved single-check Fast contract')
        if command == 'duel':
            sub.add_argument('--seed', type=int, required=True)
        else:
            sub.add_argument('--master-seed', type=int, required=True)
            sub.add_argument('--n', type=int, required=True)
    args = parser.parse_args()
    if args.command == 'extract-pdf':
        payload = extract_draft(args.pdf)
        write_json(args.output, payload)
        print(f"PDF evidence extracted: {len(payload['form_fields'])} fields; review required")
    elif args.command == 'validate':
        report = coverage(load_sheet(args.sheet))
        if args.output:
            write_json(args.output, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if not report['ready_for_this_scope']:
            raise SystemExit(2)
    else:
        if args.output.exists():
            parser.error('Output already exists; choose a new versioned filename')
        policies = {s.id: s.policy for s in strategies()}
        policies.update(attack=ATTACK, kiter=KITER)
        if args.policy not in policies or args.opponent_policy not in policies:
            parser.error(f"Policy must be one of {sorted(policies)}")
        sheets = (load_sheet(args.hero), load_sheet(args.opponent))
        if sheets[0].ruleset == LEGACY_RULESET and not args.historical_rules:
            parser.error('This sheet uses historical table rules; use the current sheet revision or --historical-rules')
        selected_policies = (policies[args.policy], policies[args.opponent_policy])
        if args.positions is not None and args.corridor_length is None:
            parser.error('--positions requires --corridor-length')
        battlefield = None
        if args.corridor_length is not None:
            try:
                battlefield = CorridorMap(args.corridor_length, tuple(args.positions or (0, 8)))
            except ValueError as exc:
                parser.error(str(exc))
        if (args.wall_aware or args.opponent_wall_aware) and sheets[0].ruleset != CURRENT_RULESET:
            parser.error('The new wall-aware policy requires the current table ruleset')
        if sheets[0].ruleset == CURRENT_RULESET:
            selected_policies = tuple(
                (WallAwarePolicy if aware else SplitFastPolicy)(**asdict(policy), effect_limb=limb)
                for policy, limb, aware in zip(selected_policies,
                                               (args.effect_limb, args.opponent_effect_limb),
                                               (args.wall_aware, args.opponent_wall_aware)))
        if args.command == 'duel':
            payload = run_duel(*sheets, *selected_policies,
                               seed=args.seed, initial_distance=args.distance, battlefield=battlefield)
        else:
            payload = run_batch(*sheets, *selected_policies, n=args.n,
                                master_seed=args.master_seed,
                                initial_distance=args.distance, battlefield=battlefield)
        sources = dict(payload['source_sha256'])
        sources['scripts/character_sheet.py'] = sha256(Path(__file__).read_bytes()).hexdigest()
        for name in (args.hero, args.opponent):
            resolved = name.resolve()
            sources[str(resolved)] = sha256(resolved.read_bytes()).hexdigest()
        payload['source_sha256'] = sources
        write_json(args.output, payload)
        if args.command == 'duel':
            print(f"{payload['hero_outcome']}; winner={payload['result']['winner']}; audit=OK")
        else:
            print(f"{payload['n']} duels: {payload['outcomes']}; "
                  f"{len(payload['audited_traces'])} full traces audited")


if __name__ == '__main__':
    main()
