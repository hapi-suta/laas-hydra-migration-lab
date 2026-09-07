#!/usr/bin/env python3
"""Authoring-only snapshot copy for localhost databases. This is NOT the DMS lesson."""
import argparse
import json
from pathlib import Path
from db import connections, ident, canonical


def main():
    import pymysql
    from psycopg.types.json import Jsonb, Json
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--disposable-target', action='store_true')
    a = p.parse_args()
    if not a.disposable_target:
        p.error('This clears selected local target tables; --disposable-target is required')
    conf = json.loads(Path('runtime/databases.json').read_text())
    if any(conf[n]['host'] not in ('127.0.0.1', 'localhost') for n in ('source', 'target')):
        raise SystemExit('Local copy refuses cloud or remote databases. Use DMS there.')
    report = json.loads(Path('evidence/inventory.json').read_text())
    if not report.get('reviewed') or not all(t['column_match'] for t in report['tables']):
        raise SystemExit('Reviewed compatible inventory required')
    source, target = connections()
    with target.transaction():
        with target.cursor() as dest:
            dest.execute("SET LOCAL session_replication_role='replica'")
            dest.execute('TRUNCATE ' + ','.join('public.' + ident(t['table'], 'pg') for t in report['tables']))
            for t in report['tables']:
                cols = list(t['source_columns'])
                with source.cursor(pymysql.cursors.SSCursor) as src:
                    src.execute('SELECT ' + ','.join(map(ident, cols)) + ' FROM ' + ident(t['table']))
                    query = 'INSERT INTO public.' + ident(t['table'], 'pg') + '(' + ','.join(ident(c, 'pg') for c in cols) + ') VALUES (' + ','.join(['%s'] * len(cols)) + ')'
                    count = 0
                    while True:
                        rows = src.fetchmany(500)
                        if not rows:
                            break
                        adapted = []
                        for row in rows:
                            out = []
                            for col, val in zip(cols, row):
                                typ = t['target_columns'][col]
                                if val is not None and typ in ('json', 'jsonb'):
                                    val = (Jsonb if typ == 'jsonb' else Json)(canonical(val, typ))
                                elif val is not None and typ in ('boolean', 'uuid'):
                                    val = canonical(val, typ)
                                out.append(val)
                            adapted.append(out)
                        dest.executemany(query, adapted)
                        count += len(rows)
                    print(t['table'], count, flush=True)
    source.close()
    target.close()
    print('Local authoring snapshot copied. Cloud DMS validation is still required.')


if __name__ == '__main__':
    main()
