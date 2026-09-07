#!/usr/bin/env python3
"""Produce exact-table DMS selection with an explicit MySQL database -> PG schema mapping."""
import argparse
import json
from pathlib import Path


def build(report, source_database='hydra', target_schema='public'):
    if report.get('reviewed') is not True:
        raise ValueError('Inventory must be reviewed explicitly before generating mappings')
    tables = report.get('tables', [])
    if not tables:
        raise ValueError('Empty table selection')
    names = [t['table'] for t in tables]
    if len(set(names)) != len(names):
        raise ValueError('Duplicate table selection')
    rules = []
    for i, table in enumerate(tables, 1):
        if not table.get('column_match') or not table.get('primary_key'):
            raise ValueError('Resolve missing columns/primary keys: ' + table['table'])
        rules.append({'rule-type': 'selection', 'rule-id': str(i), 'rule-name': 'include-' + str(i), 'object-locator': {'schema-name': source_database, 'table-name': table['table']}, 'rule-action': 'include'})
    rules.append({'rule-type': 'transformation', 'rule-id': str(len(rules) + 1), 'rule-name': 'target-schema', 'rule-target': 'schema', 'object-locator': {'schema-name': source_database}, 'rule-action': 'rename', 'value': target_schema})
    return {'rules': rules}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inventory', default='evidence/inventory.json')
    p.add_argument('--output', default='runtime/table-mappings.json')
    a = p.parse_args()
    result = build(json.loads(Path(a.inventory).read_text()))
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(result, indent=2))
    print('Exact table mappings written to ' + a.output)
