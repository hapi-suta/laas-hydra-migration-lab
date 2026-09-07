#!/usr/bin/env python3
"""Bulk scale genuine Hydra client rows. API workload is a separate, required exercise.

This profile deliberately models client/metadata-heavy volume. It does not claim
to be a customer-measured session/token distribution. Source schema is untouched.
"""
import argparse
import base64
import json
import random
import time
import uuid
from pathlib import Path
from db import ident


def payload(row_id, size):
    rng = random.Random(row_id)
    return json.dumps({'lab': 'hydra-migration', 'cohort': row_id % 25, 'ordinal': row_id, 'unicode': 'Montréal 東京', 'description': base64.b64encode(rng.randbytes((size * 3 + 3) // 4)).decode()[:size]}, ensure_ascii=False)


def main():
    import pymysql
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', default='runtime/databases.json')
    p.add_argument('--gib', type=float, default=0.05)
    p.add_argument('--batch', type=int, default=500)
    p.add_argument('--metadata-bytes', type=int, default=8192)
    p.add_argument('--full-scale', action='store_true', help='Required for a dataset greater than 1 GiB')
    a = p.parse_args()
    if a.gib <= 0 or a.batch < 1 or not 256 <= a.metadata_bytes <= 32000:
        p.error('Require positive size/batch and metadata bytes between 256 and 32000')
    if a.gib > 1 and not a.full_scale:
        p.error('Use --full-scale to request a large, resource-consuming dataset')
    conf = json.loads(Path(a.config).read_text())
    con = pymysql.connect(**conf['source'], autocommit=False)
    with con.cursor() as c:
        c.execute('SELECT * FROM hydra_client WHERE id=%s', ('lab-portal',))
        template = c.fetchone()
        if not template:
            raise SystemExit('Start the portal first; its API-created template client is required.')
        columns = [x[0] for x in c.description]
        for required in ('id', 'metadata', 'client_name', 'nid'):
            if required not in columns:
                raise SystemExit('Unsupported schema: missing ' + required)
        c.execute("SELECT COALESCE(MAX(CAST(SUBSTRING(id,11) AS UNSIGNED)),0) FROM hydra_client WHERE id REGEXP '^lab-scale-[0-9]+$'")
        row_id = int(c.fetchone()[0]) + 1
        # Compute bytes from actual values, not InnoDB page allocation or Aurora cluster volume.
        expr = '+'.join('COALESCE(OCTET_LENGTH(' + ident(col) + '),0)' for col in columns)
        print('Measuring existing client data; a full scan can take time.', flush=True)
        c.execute('SELECT COALESCE(SUM(' + expr + '),0) FROM hydra_client')
        logical_bytes = int(c.fetchone()[0])
        goal = int(a.gib * 1024**3)
        inserts = 'INSERT INTO hydra_client (' + ','.join(map(ident, columns)) + ') VALUES (' + ','.join(['%s'] * len(columns)) + ')'
        start = time.time()
        while logical_bytes < goal:
            rows = []
            added = 0
            for _ in range(a.batch):
                row = list(template)
                row[columns.index('id')] = f'lab-scale-{row_id:012d}'
                row[columns.index('client_name')] = f'Practice client {row_id}'
                if 'pk' in columns:
                    row[columns.index('pk')] = str(uuid.uuid5(uuid.NAMESPACE_URL, f'hydra-practice-client:{row_id}'))
                row[columns.index('metadata')] = payload(row_id, a.metadata_bytes + (row_id % 7) * 128)
                rows.append(row)
                added += sum(len(v if isinstance(v, bytes) else str(v).encode()) for v in row if v is not None)
                row_id += 1
            c.executemany(inserts, rows)
            con.commit()
            logical_bytes += added
            print(json.dumps({'client_logical_gib_estimate': round(logical_bytes / 1024**3, 4), 'last_id': row_id - 1, 'seconds': round(time.time() - start)}), flush=True)
        c.execute('SELECT COALESCE(SUM(' + expr + '),0),COUNT(*) FROM hydra_client')
        measured, count = c.fetchone()
        report = {'profile': 'client-metadata-heavy', 'measured_client_logical_bytes': int(measured), 'rows': count, 'requested_gib': a.gib, 'meets_goal': int(measured) >= goal, 'notes': 'Indexes/storage overhead excluded. API token workload required separately. Not a measured production distribution.'}
        Path('evidence').mkdir(exist_ok=True)
        Path('evidence/scale.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
        if not report['meets_goal']:
            raise SystemExit('Exact measurement is below goal; rerun to top up.')
    con.close()


if __name__ == '__main__':
    main()
