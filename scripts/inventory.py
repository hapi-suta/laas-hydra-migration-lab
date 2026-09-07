#!/usr/bin/env python3
"""Generate a reviewable exact table inventory; never infer selection from hydra_* alone."""
import argparse
import json
from pathlib import Path
from db import connections, schema, ident


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', default='runtime/databases.json')
    p.add_argument('--output', default='evidence/inventory.json')
    a = p.parse_args()
    source, target = connections(a.config)
    src, dst = schema(source, target)
    report = {'reviewed': False, 'tables': [], 'excluded': [], 'target_only': sorted(set(dst) - set(src))}
    for table, columns in src.items():
        if 'migration' in table:
            report['excluded'].append({'table': table, 'reason': 'Migration bookkeeping: review and retain target-native history'})
            continue
        with source.cursor() as c:
            c.execute('SELECT COUNT(*) FROM ' + ident(table))
            count = c.fetchone()[0]
            c.execute("SELECT column_name FROM information_schema.key_column_usage WHERE table_schema=DATABASE() AND table_name=%s AND constraint_name='PRIMARY' ORDER BY ordinal_position", (table,))
            pk = [r[0] for r in c]
        report['tables'].append({'table': table, 'rows': count, 'primary_key': pk, 'source_columns': columns, 'target_columns': dst.get(table, {}), 'column_match': set(columns) == set(dst.get(table, {}))})
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(f'Wrote {out}; {len(report["tables"])} data tables. Review exclusions, types, keys, and set reviewed=true before mapping.')
    source.close()
    target.close()


if __name__ == '__main__':
    main()
