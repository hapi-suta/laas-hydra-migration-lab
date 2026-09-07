#!/usr/bin/env python3
"""Check empty target before load, then check foreign keys and repair owned sequences after CDC."""
import argparse
import json
from pathlib import Path
from db import connections, ident

def sequence_reset(maximum, minimum, increment):
    if increment <= 0:
        raise ValueError('Descending sequences require a separate reviewed reset policy')
    if maximum is None or maximum < minimum:
        return minimum, False
    return maximum, True


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['prepare', 'empty', 'integrity'])
    p.add_argument('--disposable-target', action='store_true')
    p.add_argument('--hydra-stopped', action='store_true')
    p.add_argument('--config', default='runtime/databases.json')
    a = p.parse_args()
    source, target = connections(a.config)
    manifest = json.loads(Path('evidence/inventory.json').read_text())
    if not manifest.get('reviewed') or not manifest.get('tables'):
        raise SystemExit('Reviewed inventory required')
    names = [t['table'] for t in manifest['tables']]
    result = {'pass': True, 'checks': []}
    if a.action == 'prepare':
        if not a.disposable_target or not a.hydra_stopped or 'networks' not in names:
            raise SystemExit('Preparing a target requires --disposable-target --hydra-stopped and a reviewed networks table.')
        with target.transaction():
            with target.cursor() as c:
                c.execute('LOCK TABLE ' + ','.join('public.' + ident(n, 'pg') for n in names) + ' IN ACCESS EXCLUSIVE MODE')
                for table in names:
                    c.execute('SELECT COUNT(*) FROM public.' + ident(table, 'pg'))
                    count = c.fetchone()[0]
                    if (table != 'networks' and count != 0) or (table == 'networks' and count > 1):
                        raise SystemExit('Target contains application data; refusing seed cleanup: ' + table)
                c.execute('DELETE FROM public.networks')
                result['checks'].append({'removed_native_seed_rows': c.rowcount})
        Path('evidence/target-prepare.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(result))
        source.close()
        target.close()
        return
    with target.cursor() as c:
        if a.action == 'empty':
            for table in names:
                c.execute('SELECT EXISTS(SELECT 1 FROM public.' + ident(table, 'pg') + ' LIMIT 1)')
                empty = not c.fetchone()[0]
                result['checks'].append({'table': table, 'empty': empty})
                result['pass'] &= empty
        else:
            c.execute("""SELECT co.conname,ns.nspname,child.relname,pns.nspname,parent.relname,
                       array_agg(ca.attname ORDER BY ck.ord),array_agg(pa.attname ORDER BY ck.ord)
                       FROM pg_constraint co JOIN pg_class child ON child.oid=co.conrelid
                       JOIN pg_namespace ns ON ns.oid=child.relnamespace
                       JOIN pg_class parent ON parent.oid=co.confrelid
                       JOIN pg_namespace pns ON pns.oid=parent.relnamespace
                       CROSS JOIN LATERAL unnest(co.conkey) WITH ORDINALITY ck(attnum,ord)
                       JOIN pg_attribute ca ON ca.attrelid=child.oid AND ca.attnum=ck.attnum
                       JOIN pg_attribute pa ON pa.attrelid=parent.oid AND pa.attnum=co.confkey[ck.ord]
                       WHERE co.contype='f' AND ns.nspname='public'
                       GROUP BY co.conname,ns.nspname,child.relname,pns.nspname,parent.relname""")
            for constraint, ns, child, pns, parent, cols, pcols in c.fetchall():
                if child not in names:
                    continue
                conditions = ' AND '.join('c.' + ident(col, 'pg') + ' IS NOT NULL' for col in cols)
                joins = ' AND '.join('c.' + ident(col, 'pg') + '=p.' + ident(pcol, 'pg') for col, pcol in zip(cols, pcols))
                query = 'SELECT COUNT(*) FROM ' + ident(ns, 'pg') + '.' + ident(child, 'pg') + ' c WHERE ' + conditions + ' AND NOT EXISTS (SELECT 1 FROM ' + ident(pns, 'pg') + '.' + ident(parent, 'pg') + ' p WHERE ' + joins + ')'
                c.execute(query)
                orphans = c.fetchone()[0]
                result['checks'].append({'constraint': constraint, 'orphans': orphans})
                result['pass'] &= orphans == 0
            for t in manifest['tables']:
                for col in t['target_columns']:
                    c.execute('SELECT pg_get_serial_sequence(%s,%s)', ('public.' + ident(t['table'], 'pg'), col))
                    seq = c.fetchone()[0]
                    if seq:
                        c.execute('SELECT MAX(' + ident(col, 'pg') + ') FROM public.' + ident(t['table'], 'pg'))
                        maximum = c.fetchone()[0]
                        c.execute('SELECT seqmin,seqincrement FROM pg_sequence WHERE seqrelid=%s::regclass', (seq,))
                        minimum, increment = c.fetchone()
                        value, called = sequence_reset(maximum, minimum, increment)
                        c.execute('SELECT setval(%s,%s,%s)', (seq, value, called))
                        result['checks'].append({'sequence': seq, 'reset_value': value, 'is_called': called})
    Path('evidence/target-' + a.action + '.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    source.close()
    target.close()
    if not result['pass']:
        raise SystemExit('Target check failed')


if __name__ == '__main__':
    main()
