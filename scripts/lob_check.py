#!/usr/bin/env python3
"""Scan actual LOB lengths for every reviewed table before using 64 KiB limited LOB mode."""
import argparse
import json
from pathlib import Path
from db import connections, ident


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', default='runtime/databases.json')
    a = p.parse_args()
    source, target = connections(a.config)
    report = json.loads(Path('evidence/inventory.json').read_text())
    if not report.get('reviewed'):
        raise SystemExit('Review inventory first.')
    result = {'limit_bytes': 65536, 'pass': True, 'columns': []}
    with source.cursor() as c:
        for table in report['tables']:
            for col, typ in table['source_columns'].items():
                if typ in ('text', 'tinytext', 'mediumtext', 'longtext', 'blob', 'tinyblob', 'mediumblob', 'longblob', 'json'):
                    c.execute('SELECT COALESCE(MAX(OCTET_LENGTH(' + ident(col) + ')),0) FROM ' + ident(table['table']))
                    size = int(c.fetchone()[0])
                    result['columns'].append({'table': table['table'], 'column': col, 'max_bytes': size})
                    result['pass'] = result['pass'] and size <= 65536
    Path('evidence/lob-check.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    source.close()
    target.close()
    if not result['pass']:
        raise SystemExit('LOB limit exceeded. Revise task settings and validation before starting DMS.')
