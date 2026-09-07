#!/usr/bin/env python3
"""Read every selected row from both engines and compare canonical values by primary key.

Run only after fencing writers and finishing CDC. Bounded memory, but scans all data.
No token values or row content are written to the report.
"""
import argparse
import hashlib
import json
from pathlib import Path
from db import connections, canonical, ident


def digest_rows(cursor, types):
    total = 0
    # Commutative 256-bit sum permits different collation order; PKs are included.
    digest = 0
    while True:
        rows = cursor.fetchmany(500)
        if not rows:
            break
        for row in rows:
            encoded = json.dumps([canonical(v, typ) for v, typ in zip(row, types)], sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
            digest = (digest + int.from_bytes(hashlib.sha256(encoded).digest(), 'big')) % (1 << 256)
            total += 1
    return {'rows': total, 'sha256_sum': f'{digest:064x}'}


def main():
    import pymysql
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', default='runtime/databases.json')
    p.add_argument('--writers-fenced', action='store_true')
    a = p.parse_args()
    if not a.writers_fenced:
        p.error('Fence every application/workload writer first, then pass --writers-fenced')
    source, target = connections(a.config)
    manifest = json.loads(Path('evidence/inventory.json').read_text())
    if not manifest.get('reviewed') or not manifest.get('tables'):
        raise SystemExit('Reviewed nonempty inventory required')
    report = {'pass': True, 'tables': [], 'method': 'all-row canonical SHA256 sum + exact count; writers fenced'}
    for t in manifest['tables']:
        if not t['column_match']:
            raise SystemExit('Column mismatch: ' + t['table'])
        columns = sorted(t['source_columns'])
        types = [t['target_columns'][col] for col in columns]
        with source.cursor(pymysql.cursors.SSCursor) as c:
            c.execute('SELECT ' + ','.join(ident(col) for col in columns) + ' FROM ' + ident(t['table']))
            before = digest_rows(c, types)
        # A server-side cursor bounds memory for the PostgreSQL scan.
        with target.transaction():
            with target.cursor(name='reconcile') as c:
                c.execute('SELECT ' + ','.join(ident(col, 'pg') for col in columns) + ' FROM public.' + ident(t['table'], 'pg'))
                after = digest_rows(c, types)
        passed = before == after
        report['tables'].append({'table': t['table'], 'source': before, 'target': after, 'pass': passed})
        report['pass'] = report['pass'] and passed
        print(t['table'], 'PASS' if passed else 'FAIL', before['rows'], after['rows'], flush=True)
    Path('evidence/reconciliation.json').write_text(json.dumps(report, indent=2))
    source.close()
    target.close()
    if not report['pass']:
        raise SystemExit('Reconciliation failed. Cutover is blocked.')


if __name__ == '__main__':
    main()
