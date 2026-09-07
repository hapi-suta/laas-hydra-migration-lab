#!/usr/bin/env python3
"""Local demo lifecycle. No AWS resources are modified by this script."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def env():
    return dict(line.split('=', 1) for line in (ROOT / '.env').read_text().splitlines() if line and not line.startswith('#'))


def private_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w') as f:
        f.write(text)
    path.chmod(0o600)


def compose(*args):
    subprocess.run(['docker', 'compose', *args], cwd=ROOT, check=True, timeout=900)


def wait_ready(url):
    for _ in range(90):
        try:
            with urlopen(url, timeout=3) as r:
                if r.status == 200:
                    return
        except Exception:
            pass
        time.sleep(2)
    raise SystemExit('Service did not become ready: ' + url)


def init():
    if (ROOT / '.env').exists():
        print('Existing credentials preserved.')
        return
    names = ['MYSQL_ROOT_PASSWORD', 'MYSQL_PASSWORD', 'POSTGRES_PASSWORD', 'HYDRA_SYSTEM_SECRET', 'HYDRA_COOKIE_SECRET', 'PORTAL_CLIENT_SECRET']
    values = {key: secrets.token_hex(24) for key in names}
    private_write(ROOT / '.env', ''.join(f'{k}={v}\n' for k, v in values.items()))
    private_write(ROOT / 'runtime/active.json', '{"active":"source"}\n')
    private_write(ROOT / 'runtime/upstream.conf', 'upstream hydra_active { server source:4444; }\n')
    config = {'source': {'host': '127.0.0.1', 'port': 13306, 'user': 'hydra', 'password': values['MYSQL_PASSWORD'], 'database': 'hydra'},
              'target': {'host': '127.0.0.1', 'port': 15432, 'user': 'hydra', 'password': values['POSTGRES_PASSWORD'], 'dbname': 'hydra', 'sslmode': 'disable'}}
    private_write(ROOT / 'runtime/databases.json', json.dumps(config, indent=2))
    print('Created private .env and runtime configuration. Credentials are not printed.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['init', 'up', 'status', 'stop', 'start-target', 'switch-target', 'switch-source', 'logs'])
    args = parser.parse_args()
    if args.action == 'init':
        init()
    elif args.action == 'up':
        compose('up', '-d', '--build')
        wait_ready('http://localhost:8080/health')
        print('Portal: http://localhost:8080 — sign in as Alice or Bob.')
    elif args.action == 'status':
        compose('ps', '-a')
        print((ROOT / 'runtime/active.json').read_text())
    elif args.action == 'stop':
        compose('stop')
    elif args.action == 'logs':
        compose('logs', '--tail', '60', 'source', 'target', 'portal')
    elif args.action == 'start-target':
        compose('--profile', 'target', 'up', '-d', 'target')
        wait_ready('http://localhost:5445/health/ready')
    else:
        target = args.action.removeprefix('switch-')
        if target == 'target':
            wait_ready('http://localhost:5445/health/ready')
        # Truncate/write same inode: nginx has a bind mount of this file.
        private_write(ROOT / 'runtime/upstream.conf', f'upstream hydra_active {{ server {target}:4444; }}\n')
        compose('up', '-d', '--no-deps', 'gateway')
        compose('exec', '-T', 'gateway', 'nginx', '-t')
        compose('exec', '-T', 'gateway', 'nginx', '-s', 'reload')
        private_write(ROOT / 'runtime/active.json', json.dumps({'active': target}))
        print('Demo gateway now uses ' + target + '. This is routing only; follow the cutover gate before switching.')


if __name__ == '__main__':
    main()
