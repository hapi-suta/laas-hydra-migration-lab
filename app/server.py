"""Synthetic lab portal. Tokens remain server-side; no real user credentials."""
import base64
import hashlib
import html
import json
import os
import secrets
import threading
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

ISSUER = os.getenv('ISSUER', 'http://localhost:8080')
INTERNAL = os.getenv('INTERNAL_ISSUER', 'http://gateway:8080')
PORTAL = os.getenv('PORTAL_URL', ISSUER)
CLIENT_ID = 'lab-portal'
CLIENT_SECRET = os.environ.get('CLIENT_SECRET', '')
SESSIONS = {}
LOCK = threading.Lock()


def request_json(url, method='GET', body=None, basic=None):
    headers = {}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers['Content-Type'] = 'application/json'
    if basic:
        headers['Authorization'] = 'Basic ' + base64.b64encode(basic.encode()).decode()
    with urlopen(Request(url, data=data, method=method, headers=headers), timeout=20) as r:
        return json.load(r)


def active():
    name = json.loads(Path('/runtime/active.json').read_text())['active']
    if name not in ('source', 'target'):
        raise ValueError('Invalid active database')
    return name


def admin():
    return 'http://' + active() + ':4445'


def token_request(values):
    headers = {'Content-Type': 'application/x-www-form-urlencoded',
               'Authorization': 'Basic ' + base64.b64encode(f'{CLIENT_ID}:{CLIENT_SECRET}'.encode()).decode()}
    with urlopen(Request(INTERNAL + '/oauth2/token', data=urlencode(values).encode(), headers=headers), timeout=20) as r:
        return json.load(r)


def register():
    payload = {'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET,
               'client_name': 'Hydra migration practice portal',
               'grant_types': ['authorization_code', 'refresh_token', 'client_credentials'],
               'response_types': ['code'], 'scope': 'openid offline_access profile',
               'redirect_uris': [PORTAL + '/callback'], 'token_endpoint_auth_method': 'client_secret_basic'}
    # Only initialize the source. Never create records on the migration target.
    try:
        request_json('http://source:4445/admin/clients/' + CLIENT_ID)
    except HTTPError as e:
        if e.code != 404:
            raise
        request_json('http://source:4445/admin/clients', 'POST', payload)


STYLE = '''body{margin:0;background:#eef3f6;color:#142d3e;font:17px system-ui}main{max-width:850px;margin:65px auto;padding:36px;background:white;border-radius:20px}h1{font-size:40px;letter-spacing:-1px}a,button{color:#087b72}button,.button{display:inline-block;border:0;background:#087b72;color:white;padding:13px 20px;border-radius:8px;text-decoration:none;cursor:pointer;font:inherit}small{color:#637985}pre{background:#edf5f4;padding:20px;white-space:pre-wrap;overflow-wrap:anywhere}label{display:block;margin:16px 0}.badge{display:inline-block;background:#dff4ee;padding:8px;border-radius:6px}nav{display:flex;gap:12px;flex-wrap:wrap}'''


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # OAuth query strings contain authorization codes/challenges. Do not log URLs.
        print(json.dumps({'method': self.command, 'path': urlparse(self.path).path}))

    def session(self):
        c = SimpleCookie()
        c.load(self.headers.get('Cookie', ''))
        sid = c['practice'].value if 'practice' in c else ''
        with LOCK:
            expired = [k for k, v in SESSIONS.items() if v['expires'] < time.time()]
            for k in expired:
                del SESSIONS[k]
            if sid not in SESSIONS:
                sid = secrets.token_urlsafe(32)
                SESSIONS[sid] = {'csrf': secrets.token_urlsafe(32), 'expires': time.time() + 28800}
            self.sid = sid
            return SESSIONS[sid]

    def send(self, content, status=200, location=None):
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Set-Cookie', f'practice={self.sid}; HttpOnly; SameSite=Lax; Path=/')
        if location:
            self.send_header('Location', location)
        self.end_headers()
        self.wfile.write(content.encode())

    def page(self, title, body):
        self.send(f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{html.escape(title)}</title><style>{STYLE}</style><main><small>SUTA LABS / HYDRA MIGRATION</small><h1>{html.escape(title)}</h1>{body}</main></html>')

    def form(self, route, text, extra=''):
        csrf = html.escape(self.s['csrf'])
        return f'<form method="post" action="{route}"><input type="hidden" name="csrf" value="{csrf}">{extra}<button>{text}</button></form>'

    def do_GET(self):
        self.s = self.session()
        p = urlparse(self.path)
        q = parse_qs(p.query)
        try:
            if p.path == '/health':
                return self.send('portal ready')
            if p.path == '/':
                return self.page('Your migration practice portal', f'<p class="badge">Active backend: {active()}</p><p>Use Alice or Bob, synthetic identities created only for this lab. Sign in before migration, then refresh the same session after cutover.</p><nav><a class="button" href="/signin">Sign in</a><a class="button" href="/account">Protected account</a></nav><p>No customer credentials are required.</p>')
            if p.path == '/signin':
                state = secrets.token_urlsafe(32)
                verifier = secrets.token_urlsafe(48)
                self.s.update(state=state, verifier=verifier)
                challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
                query = urlencode({'client_id': CLIENT_ID, 'response_type': 'code', 'scope': 'openid offline_access profile', 'redirect_uri': PORTAL + '/callback', 'state': state, 'code_challenge': challenge, 'code_challenge_method': 'S256'})
                return self.send('', 302, ISSUER + '/oauth2/auth?' + query)
            if p.path == '/login':
                challenge = q['login_challenge'][0]
                request_json(admin() + '/admin/oauth2/auth/requests/login?' + urlencode({'login_challenge': challenge}))
                self.s['login_challenge'] = challenge
                choices = '<label>Demo identity <select name="subject"><option>alice</option><option>bob</option></select></label>'
                return self.page('Choose a demo identity', '<p>This is a synthetic login service for migration practice.</p>' + self.form('/login', 'Continue', choices))
            if p.path == '/consent':
                challenge = q['consent_challenge'][0]
                data = request_json(admin() + '/admin/oauth2/auth/requests/consent?' + urlencode({'consent_challenge': challenge}))
                self.s['consent_challenge'] = challenge
                return self.page('Grant consent', '<p>Requested scopes: ' + html.escape(' '.join(data['requested_scope'])) + '</p>' + self.form('/consent', 'Allow'))
            if p.path == '/callback':
                state = self.s.pop('state', None)
                if not state or not secrets.compare_digest(q.get('state', [''])[0], state):
                    return self.send('Invalid OAuth state. Start sign-in again.', 400)
                result = token_request({'grant_type': 'authorization_code', 'code': q['code'][0], 'redirect_uri': PORTAL + '/callback', 'code_verifier': self.s.pop('verifier')})
                self.s['tokens'] = result
                return self.send('', 302, '/account')
            if p.path == '/account':
                token = self.s.get('tokens', {}).get('access_token')
                if not token:
                    return self.send('', 302, '/signin')
                req = Request(admin() + '/admin/oauth2/introspect', data=urlencode({'token': token}).encode(), headers={'Content-Type': 'application/x-www-form-urlencoded'})
                with urlopen(req, timeout=20) as r:
                    info = json.load(r)
                if not info.get('active'):
                    return self.send('Token is no longer active. Investigate the migration or sign in again.', 401)
                safe = {k: info.get(k) for k in ('active', 'sub', 'client_id', 'scope', 'exp')}
                return self.page('Your protected account', '<p class="badge">Verified by ' + active() + '</p><pre>' + html.escape(json.dumps(safe, indent=2)) + '</pre><p>Tokens stay on the server. This page rechecks the active Hydra database on every visit.</p>' + self.form('/refresh', 'Refresh existing token') + '<p></p>' + self.form('/logout', 'Revoke token and sign out'))
            return self.send('Not found', 404)
        except Exception as e:
            print(json.dumps({'error_type': type(e).__name__, 'route': p.path}))
            return self.page('Practice checkpoint needs attention', '<p>The authentication request failed. Check Hydra readiness, the active backend, migration state, and configured secrets. No tokens are printed in this error.</p>')

    def do_POST(self):
        self.s = self.session()
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if size > 8192:
                return self.send('Request too large', 413)
            q = parse_qs(self.rfile.read(size).decode())
            if not secrets.compare_digest(q.get('csrf', [''])[0], self.s['csrf']):
                return self.send('Invalid CSRF token', 403)
            path = urlparse(self.path).path
            if path == '/login':
                subject = q.get('subject', [''])[0]
                if subject not in ('alice', 'bob'):
                    return self.send('Unknown demo identity', 400)
                challenge = self.s.pop('login_challenge')
                result = request_json(admin() + '/admin/oauth2/auth/requests/login/accept?' + urlencode({'login_challenge': challenge}), 'PUT', {'subject': subject, 'remember': False})
                return self.send('', 302, result['redirect_to'])
            if path == '/consent':
                challenge = self.s.pop('consent_challenge')
                data = request_json(admin() + '/admin/oauth2/auth/requests/consent?' + urlencode({'consent_challenge': challenge}))
                result = request_json(admin() + '/admin/oauth2/auth/requests/consent/accept?' + urlencode({'consent_challenge': challenge}), 'PUT', {'grant_scope': data['requested_scope'], 'grant_access_token_audience': data.get('requested_access_token_audience', []), 'remember': False, 'session': {'id_token': {'name': data['subject'].title()}, 'access_token': {'lab': 'migration'}}})
                return self.send('', 302, result['redirect_to'])
            if path == '/refresh':
                previous = self.s['tokens']
                result = token_request({'grant_type': 'refresh_token', 'refresh_token': previous['refresh_token']})
                self.s['tokens'] = {**previous, **result}
                return self.send('', 302, '/account')
            if path == '/logout':
                token = self.s.get('tokens', {}).get('refresh_token') or self.s.get('tokens', {}).get('access_token')
                if token:
                    auth = base64.b64encode(f'{CLIENT_ID}:{CLIENT_SECRET}'.encode()).decode()
                    with urlopen(Request(INTERNAL + '/oauth2/revoke', data=urlencode({'token': token}).encode(), headers={'Authorization': 'Basic ' + auth}), timeout=20):
                        pass
                self.s.pop('tokens', None)
                return self.send('', 302, '/')
            return self.send('Not found', 404)
        except Exception as e:
            print(json.dumps({'error_type': type(e).__name__, 'route': urlparse(self.path).path}))
            return self.send('Operation failed. Check the active Hydra backend and server logs.', 502)


if __name__ == '__main__':
    for attempt in range(90):
        try:
            register()
            break
        except Exception:
            time.sleep(2)
    else:
        raise SystemExit('Source Hydra did not become ready for portal registration')
    ThreadingHTTPServer(('0.0.0.0', 3000), Handler).serve_forever()
