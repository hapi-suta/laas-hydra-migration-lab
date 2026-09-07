#!/usr/bin/env python3
"""Create real token, client update/delete, and revocation activity through Hydra APIs."""
import argparse
import base64
import concurrent.futures
import json
from pathlib import Path
import secrets
import threading
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from lab import env


def call(url, data=None, method=None, auth=None, form=False):
    headers = {}
    if auth:
        headers['Authorization'] = 'Basic ' + base64.b64encode(auth.encode()).decode()
    raw = None
    if data is not None:
        raw = (urlencode(data) if form else json.dumps(data)).encode()
        headers['Content-Type'] = 'application/x-www-form-urlencoded' if form else 'application/json'
    with urlopen(Request(url, data=raw, method=method, headers=headers), timeout=30) as r:
        text = r.read()
        return json.loads(text) if text else {}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seconds', type=int, default=60)
    p.add_argument('--workers', type=int, default=2)
    p.add_argument('--rps', type=float, default=2, help='Token cycles per second across all workers')
    p.add_argument('--public-url', default='http://localhost:8080')
    p.add_argument('--admin-url', default='http://127.0.0.1:4445')
    a = p.parse_args()
    if a.workers < 1 or a.workers > 32 or a.seconds < 1 or a.rps <= 0:
        p.error('workers 1..32, seconds and rps positive')
    auth = 'lab-portal:' + env()['PORTAL_CLIENT_SECRET']
    deadline = time.monotonic() + a.seconds
    lock = threading.Lock()
    stats = {'token_issued': 0, 'revoked': 0, 'clients_created_updated_deleted': 0, 'errors': 0}
    def worker(n):
        i = 0
        while time.monotonic() < deadline:
            started = time.monotonic()
            try:
                token = call(a.public_url + '/oauth2/token', {'grant_type': 'client_credentials', 'scope': 'profile'}, auth=auth, form=True)
                with lock:
                    stats['token_issued'] += 1
                if i % 4 == 0:
                    call(a.public_url + '/oauth2/revoke', {'token': token['access_token']}, auth=auth, form=True)
                    with lock:
                        stats['revoked'] += 1
                if i % 20 == 0:
                    cid = 'lab-churn-' + secrets.token_hex(8)
                    row = call(a.admin_url + '/admin/clients', {'client_id': cid, 'grant_types': ['client_credentials'], 'scope': 'profile', 'metadata': {'phase': 'created'}})
                    row['metadata'] = {'phase': 'updated', 'worker': n}
                    call(a.admin_url + '/admin/clients/' + cid, row, method='PUT')
                    call(a.admin_url + '/admin/clients/' + cid, method='DELETE')
                    with lock:
                        stats['clients_created_updated_deleted'] += 1
            except Exception as exc:
                with lock:
                    stats['errors'] += 1
                print('Workload error:', type(exc).__name__, flush=True)
            i += 1
            time.sleep(max(0, a.workers / a.rps - (time.monotonic() - started)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
        list(pool.map(worker, range(a.workers)))
    Path('evidence').mkdir(exist_ok=True)
    Path('evidence/workload.json').write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))
    if stats['errors'] or not stats['token_issued']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
