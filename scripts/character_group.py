"""Run one experimental fixed-contact group from a JSON configuration."""

from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path

from blacklight.experiment import ROOT
from blacklight.results_io import require_new_output, require_unchanged_sources, write_new_text
from combatants.group import GroupPolicy
from combatants.group_runner import run_group
from combatants.sheets import parse_sheet


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.is_relative_to((ROOT / 'results').resolve()):
        parser.error('Experimental group output must stay outside the frozen results directory')
    require_new_output(output)
    config_path = args.config.resolve()
    config_bytes = config_path.read_bytes()
    config = json.loads(config_bytes.decode('utf-8'))
    if (not isinstance(config, dict)
            or set(config) != {'schema', 'seed', 'max_rounds', 'initiative_tie_order', 'combatants'}
            or config['schema'] != 'blacklight.experimental-group-config.v1'
            or not isinstance(config['combatants'], list) or len(config['combatants']) < 2):
        raise ValueError('Invalid experimental group configuration')
    script = Path(__file__).resolve()
    inputs = {script: script.read_bytes(), config_path: config_bytes}
    sheets, policies, teams, roles = [], [], [], []
    for row in config['combatants']:
        if (not isinstance(row, dict) or set(row) != {'sheet', 'team', 'role', 'policy'}
                or not isinstance(row['sheet'], str) or not row['sheet']
                or not isinstance(row['policy'], dict)):
            raise ValueError('Each combatant needs a sheet path, team, role and policy mapping')
        path = (config_path.parent / row['sheet']).resolve()
        content = path.read_bytes()
        if path in inputs and inputs[path] != content:
            raise RuntimeError('Input changed while reading configuration')
        inputs[path] = content
        sheets.append(parse_sheet(json.loads(content.decode('utf-8'))))
        policies.append(GroupPolicy(**row['policy']))
        teams.append(row['team'])
        roles.append(row['role'])
    order = config['initiative_tie_order']
    if order is not None and not isinstance(order, list):
        raise ValueError('The optional tie order must be a list')
    payload = run_group(tuple(sheets), tuple(policies), teams=tuple(teams),
                        initiative_roles=tuple(roles),
                        initiative_tie_order=tuple(order) if order is not None else None,
                        seed=config['seed'], max_rounds=config['max_rounds'])
    before = {str(path): sha256(content).hexdigest() for path, content in inputs.items()}
    after = {str(path): sha256(path.read_bytes()).hexdigest() for path in inputs}
    require_unchanged_sources(before, after)
    payload['input_source_sha256'] = before
    write_new_text(output, json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"Experimental group: {payload['result']['outcome']}; "
          f"winner={payload['result']['winner']}; partial audits passed")


if __name__ == '__main__':
    main()
