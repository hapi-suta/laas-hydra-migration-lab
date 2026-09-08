#!/usr/bin/env python3
"""Exercise the real portal OAuth flow and preserve its private cookie for cutover checks."""
import argparse
from html.parser import HTMLParser
import http.cookiejar
import json
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.error import HTTPError
from urllib.request import build_opener, HTTPCookieProcessor, Request, ProxyHandler


class Form(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values = {}
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'input' and attrs.get('name'):
            self.values[attrs['name']] = attrs.get('value', '')


class Account(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_pre = False
        self.text = []
    def handle_starttag(self, tag, attrs):
        if tag == 'pre': self.in_pre = True
    def handle_endtag(self, tag):
        if tag == 'pre': self.in_pre = False
    def handle_data(self, data):
        if self.in_pre: self.text.append(data)


def verify_account(path, body, backend, subject):
    assert path == '/account' and 'Your protected account' in body, 'Protected account verification failed'
    assert 'Verified by ' + backend in body, 'Unexpected backend'
    parser = Account()
    parser.feed(body)
    info = json.loads(''.join(parser.text))
    assert info['active'] is True, 'Inactive token'
    assert info['sub'] == subject, 'Subject changed'
    assert info['client_id'] == 'lab-portal', 'Unexpected OAuth client'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['login', 'check', 'refresh', 'revoke'])
    p.add_argument('--base', default='http://localhost:8080')
    p.add_argument('--subject', choices=['alice', 'bob'], default='alice')
    p.add_argument('--cookie', default='runtime/probe.cookies')
    p.add_argument('--expect-backend', choices=['source', 'target'], default='source')
    a = p.parse_args()
    cookie = Path(a.cookie)
    cookie.parent.mkdir(parents=True, exist_ok=True)
    jar = http.cookiejar.MozillaCookieJar(str(cookie))
    if cookie.exists(): jar.load(ignore_discard=True, ignore_expires=True)
    opener = build_opener(ProxyHandler({}), HTTPCookieProcessor(jar))
    def fetch(path, values=None):
        data = urlencode(values).encode() if values is not None else None
        with opener.open(Request(a.base + path, data=data), timeout=40) as r:
            return urlparse(r.url).path, r.read().decode()
    def form(body):
        parser = Form()
        parser.feed(body)
        return parser.values
    try:
        if a.action == 'login':
            path, body = fetch('/signin')
            assert path == '/login', 'Expected login page'
            path, body = fetch('/login', {**form(body), 'subject': a.subject})
            assert path == '/consent', 'Expected consent page'
            path, body = fetch('/consent', form(body))
        else:
            path, body = fetch('/account')
        verify_account(path, body, a.expect_backend, a.subject)
        if a.action in ('refresh', 'revoke'):
            route = '/refresh' if a.action == 'refresh' else '/logout'
            path, body = fetch(route, form(body))
            if a.action == 'refresh':
                verify_account(path, body, a.expect_backend, a.subject)
            else:
                assert path == '/' and 'Hydra rejected the revoked refresh token' in body, 'Revocation was not verified'
                path, body = fetch('/account')
                assert path == '/login', 'Signed-out session still has protected access'
        jar.save(ignore_discard=True, ignore_expires=True)
        cookie.chmod(0o600)
        result = {'pass': True, 'action': a.action, 'backend': a.expect_backend, 'subject': a.subject}
    except Exception as e:
        result = {'pass': False, 'action': a.action, 'error_type': type(e).__name__}
        if isinstance(e, HTTPError):
            result.update(http_status=e.code, route=urlparse(e.url).path)
    out = Path('evidence/oauth-' + a.action + '-' + a.expect_backend + '.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2))
    print(json.dumps(result))
    if not result['pass']: raise SystemExit(1)


if __name__ == '__main__':
    main()
