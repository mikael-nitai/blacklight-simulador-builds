"""Reproduce fixed illustrative holdout-scenario duels, not statistical samples."""

from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path

from blacklight.results_io import require_new_output, require_unchanged_sources, write_new_text
from combatants.runner import run_duel
from scripts.current_study_dev import INPUTS, ROOT, declared_sources, source_commit
from scripts.current_study_holdout import SPEC, holdout_configurations

# Fixed before inspecting any of these examples. They are demonstrations,
# not the seeds or summaries of the preregistered statistical batches.
CASES = {'mirror_blade': 146001, 'rank4_sturdy2': 146002, 'gunner_open': 146003}
POLICY = 'hammer_fast_hammer'


def demonstration(scenario, output):
    if scenario not in CASES:
        raise ValueError('Unknown demonstration scenario')
    path = Path(output)
    if path.resolve().is_relative_to((ROOT / 'results').resolve()):
        raise ValueError('Illustrative logs belong outside frozen statistical results')
    require_new_output(path)
    inputs = tuple(p.read_bytes() for p in INPUTS)
    hero, policies, scenarios = holdout_configurations(inputs)
    opponent, opponent_policy, distance, board = scenarios[scenario]
    policy = policies[POLICY]
    extras = (SPEC, ROOT / 'scripts/current_study_holdout.py', Path(__file__).resolve())
    sources = {**declared_sources((policy, opponent_policy), board, inputs),
               **{p.relative_to(ROOT).as_posix(): sha256(p.read_bytes()).hexdigest() for p in extras}}
    commit = source_commit(sources)
    result = run_duel(hero, opponent, policy, opponent_policy, seed=CASES[scenario],
                      initial_distance=distance, max_rounds=30, battlefield=board)
    after_inputs = tuple(p.read_bytes() for p in INPUTS)
    after = {**declared_sources((policy, opponent_policy), board, after_inputs),
             **{p.relative_to(ROOT).as_posix(): sha256(p.read_bytes()).hexdigest() for p in extras}}
    require_unchanged_sources(sources, after)
    if source_commit(sources) != commit:
        raise RuntimeError('Demonstration source commit changed')
    result['source_sha256'].update(sources)
    result['demonstration'] = {'scenario': scenario, 'policy': POLICY, 'source_commit': commit,
                               'purpose': 'illustrative full audited log, not a statistical sample'}
    write_new_text(path, json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return result


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', required=True, choices=CASES)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = demonstration(args.scenario, args.output)
    print(f"Audit issues: {len(result['audit_issues'])}; complete illustrative trace saved.")


if __name__ == '__main__':
    main()
