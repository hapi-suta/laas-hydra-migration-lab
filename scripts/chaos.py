#!/usr/bin/env python3
"""Bounded, reversible application incidents for the named practice Compose project."""
import argparse
import json
from pathlib import Path
import subprocess
from urllib.request import urlopen
from lab import compose, ROOT


def healthy(url):
    try:
        with urlopen(url, timeout=5) as r:
            return r.status == 200
    except Exception:
        return False


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['inject', 'validate', 'recover'])
    p.add_argument('scenario', choices=['source-down', 'gateway-down'])
    a = p.parse_args()
    service = 'source' if a.scenario == 'source-down' else 'gateway'
    if a.action == 'inject':
        compose('stop', service)
        print('Stopped only the practice service:', service)
    elif a.action == 'recover':
        compose('start', service)
        print('Recovery requested; run validation after readiness.')
    else:
        result = {'scenario': a.scenario, 'source_ready': healthy('http://localhost:4445/health/ready'), 'portal_ready': healthy('http://localhost:8080/health')}
        result['pass'] = result['source_ready'] and result['portal_ready']
        Path('evidence').mkdir(exist_ok=True)
        Path('evidence/incident-' + a.scenario + '.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
        if not result['pass']:
            raise SystemExit(1)


if __name__ == '__main__':
    main()
