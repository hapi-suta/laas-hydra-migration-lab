import datetime
import importlib.util
import io
from unittest.mock import patch
from urllib.error import HTTPError
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
import unittest
import zipfile
import re
import subprocess
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from db import canonical, ident
from mappings import build
from reconcile import digest_rows
from cloud import engine_versions
from target_check import sequence_reset
from sct import command
from scale import payload
from oauth_probe import verify_account
portal_spec = importlib.util.spec_from_file_location('lab_portal', ROOT / 'app/server.py')
portal = importlib.util.module_from_spec(portal_spec)
portal_spec.loader.exec_module(portal)


class Cursor:
    def __init__(self, rows): self.rows = rows
    def fetchmany(self, n):
        values, self.rows = self.rows[:n], self.rows[n:]
        return values


class MigrationChecks(unittest.TestCase):
    def test_probe_rejects_wrong_subject_and_inactive_token(self):
        body = '<h1>Your protected account</h1><p>Verified by target</p><pre>{"active":true,"sub":"bob","client_id":"lab-portal"}</pre>'
        with self.assertRaises(AssertionError): verify_account('/account', body, 'target', 'alice')
        with self.assertRaises(AssertionError): verify_account('/account', body.replace('true', 'false'), 'target', 'bob')
        verify_account('/account', body, 'target', 'bob')

    def test_portal_restart_checks_target_without_creating_client(self):
        missing = HTTPError('http://target', 404, 'Not Found', {}, io.BytesIO(b'{}'))
        with patch.object(portal, 'active', return_value='target'), patch.object(portal, 'request_json', side_effect=missing) as request:
            with self.assertRaises(HTTPError): portal.register()
            self.assertEqual(request.call_count, 1)
            self.assertIn('http://target:4445/', request.call_args.args[0])

    def test_revocation_requires_refresh_rejection(self):
        with patch.object(portal, 'token_request', return_value={'access_token': 'unexpected'}):
            with self.assertRaises(RuntimeError): portal.verify_revoked_refresh('synthetic-token')
        rejected = HTTPError('http://test', 400, 'Bad Request', {}, io.BytesIO(b'{"error":"invalid_grant"}'))
        with patch.object(portal, 'token_request', side_effect=rejected):
            self.assertTrue(portal.verify_revoked_refresh('synthetic-token'))
        inactive = HTTPError('http://test', 401, 'Unauthorized', {}, io.BytesIO(b'{"error":"token_inactive"}'))
        with patch.object(portal, 'token_request', side_effect=inactive):
            self.assertTrue(portal.verify_revoked_refresh('synthetic-token'))
        unrelated = HTTPError('http://test', 400, 'Bad Request', {}, io.BytesIO(b'{"error":"invalid_client"}'))
        with patch.object(portal, 'token_request', side_effect=unrelated):
            with self.assertRaises(HTTPError): portal.verify_revoked_refresh('synthetic-token')

    def test_sct_named_parameters_and_quote_guard(self):
        self.assertEqual(command('CreateProject', name='demo'), "CreateProject -name: 'demo'\n/\n")
        with self.assertRaises(ValueError): command('AddSource', password="a'b")

    def test_scale_payload_is_sized_and_repeatable(self):
        for size in (256, 16000, 32000):
            data = payload(42, size)
            self.assertEqual(data, payload(42, size))
            self.assertEqual(len(json.loads(data)['description']), size)
            self.assertIn('東京', data)

    def test_legacy_zero_sequence_starts_at_minimum(self):
        self.assertEqual(sequence_reset(0, 1, 1), (1, False))
        self.assertEqual(sequence_reset(42, 1, 1), (42, True))
        self.assertEqual(sequence_reset(None, 1, 1), (1, False))

    def test_dms_engine_version_response(self):
        self.assertEqual(engine_versions({'EngineVersions': [{'Version': '3.6.1'}]}), ['3.6.1'])

    def test_inventory_requires_review(self):
        with self.assertRaises(ValueError): build({'reviewed': False})

    def test_empty_selection_rejected(self):
        with self.assertRaises(ValueError): build({'reviewed': True, 'tables': []})

    def test_networks_included(self):
        rules = build({'reviewed': True, 'tables': [{'table': 'networks', 'column_match': True, 'primary_key': ['id']}]})['rules']
        self.assertEqual(rules[0]['object-locator']['table-name'], 'networks')
        self.assertEqual(rules[-1]['value'], 'public')

    def test_mismatch_blocks_mapping(self):
        with self.assertRaises(ValueError): build({'reviewed': True, 'tables': [{'table': 'x', 'column_match': False, 'primary_key': ['id']}]})

    def test_canonical_boolean_json_time(self):
        self.assertEqual(canonical(1, 'boolean'), canonical(True, 'boolean'))
        self.assertEqual(canonical('{"b":2,"a":1}', 'jsonb'), {'a': 1, 'b': 2})
        utc = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
        self.assertEqual(canonical(utc), canonical(utc.replace(tzinfo=None)))

    def test_reconcile_detects_value_change(self):
        types = ['text', 'boolean']
        a = digest_rows(Cursor([('a', 1), ('b', 0)]), types)
        b = digest_rows(Cursor([('b', False), ('a', True)]), types)
        c = digest_rows(Cursor([('b', True), ('a', True)]), types)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_identifier_escaping(self):
        self.assertEqual(ident('a`b'), '`a``b`')
        self.assertEqual(ident('a"b', 'pg'), '"a""b"')

    def test_published_mapping_selects_exact_pinned_tables(self):
        mapping = json.loads((ROOT / 'migration/table-mappings-example.json').read_text())
        selected = [rule for rule in mapping['rules'] if rule['rule-type'] == 'selection']
        self.assertEqual(len(selected), 14)
        self.assertTrue(all(rule['rule-action'] == 'explicit' for rule in selected))
        names = {rule['object-locator']['table-name'] for rule in selected}
        self.assertIn('networks', names)
        self.assertNotIn('schema_migration', names)
        self.assertEqual(len(names), 14)
        settings = json.loads((ROOT / 'migration/task-settings.json').read_text())
        for route in ('console', 'build'):
            text = (ROOT / 'docs/05-dms' / (route + '.md')).read_text()
            configs = [json.loads(block) for block in re.findall(r'```json\n(.*?)\n```', text, re.S)]
            self.assertIn(mapping, configs, route + ' mapping differs from the downloadable configuration')
            self.assertIn(settings, configs, route + ' task settings differ from the downloadable configuration')

    def test_uuid_cdc_mapping_preserves_native_target(self):
        report = {'reviewed': True, 'tables': [{
            'table': 'networks', 'column_match': True, 'primary_key': ['id'],
            'source_columns': {'id': 'char'}, 'target_columns': {'id': 'uuid'},
        }]}
        rule = build(report)['rules'][-1]
        self.assertEqual(rule['rule-action'], 'change-data-type')
        self.assertEqual(rule['data-type'], {'type': 'string', 'length': 36})
        report['tables'][0]['source_columns']['id'] = 'binary'
        with self.assertRaises(ValueError):
            build(report)
        mapping = json.loads((ROOT / 'migration/table-mappings-example.json').read_text())
        uuid_rules = [r for r in mapping['rules'] if r.get('rule-action') == 'change-data-type']
        self.assertEqual(len(uuid_rules), 17)
        self.assertTrue(all(r['data-type'] == {'type': 'string', 'length': 36} for r in uuid_rules))
        self.assertIn(('hydra_client', 'nid'), {
            (r['object-locator']['table-name'], r['object-locator']['column-name']) for r in uuid_rules})

    def test_dms_no_schema_ddl_and_strict_truncation(self):
        settings = json.loads((ROOT / 'migration/task-settings.json').read_text())
        self.assertFalse(any(settings['ChangeProcessingDdlHandlingPolicy'].values()))
        self.assertEqual(settings['ErrorBehavior']['DataTruncationErrorPolicy'], 'STOP_TASK')
        self.assertTrue(settings['ValidationSettings']['EnableValidation'])


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()
    def handle_starttag(self, tag, attrs):
        for key, val in attrs:
            if key == 'id': self.ids.add(val)
        if tag in ('a', 'link', 'script', 'img'):
            for key, val in attrs:
                if key in ('href', 'src'): self.links.append(val)


class SiteChecks(unittest.TestCase):
    def test_all_local_links_resolve(self):
        pages = list((ROOT / 'site').rglob('*.html'))
        self.assertGreaterEqual(len(pages), 35)
        for path in pages:
            parser = Links()
            parser.feed(path.read_text())
            for link in parser.links:
                if link.startswith(('http:', 'https:', 'mailto:', 'data:')):
                    continue
                address, _, fragment = link.partition('#')
                target = (path.parent / unquote(address)).resolve() if address else path
                self.assertTrue(target.exists(), f'{path}: missing {link}')
                if fragment and target.suffix == '.html':
                    destination = Links()
                    destination.feed(target.read_text())
                    self.assertIn(unquote(fragment), destination.ids, f'{path}: missing anchor {link}')

    def test_student_bash_blocks_parse(self):
        for path in (ROOT / 'docs').rglob('*.md'):
            for number, block in enumerate(re.findall(r'```bash\n(.*?)```', path.read_text(), re.S), 1):
                result = subprocess.run(['bash', '-n'], input=block, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, f'{path} block {number}: {result.stderr}')

    def test_no_em_dashes_in_student_content(self):
        for path in (ROOT / 'docs').rglob('*'):
            if path.is_file() and path.suffix in ('.md', '.json', '.svg', '.js', '.css'):
                self.assertNotIn('\u2014', path.read_text(), str(path))

    def test_rds_target_lifecycle_and_engine_selections(self):
        build = (ROOT / 'docs/02-aws/build.md').read_text()
        cleanup = (ROOT / 'docs/08-handover/build.md').read_text()
        blocks = re.findall(r'```bash\n(.*?)```', build, re.S)
        target_create = [b for b in blocks if 'aws rds create-db-instance' in b and '$TARGET_DB_ID' in b]
        self.assertEqual(len(target_create), 1)
        self.assertIn('--engine postgres ', target_create[0])
        self.assertIn('--db-parameter-group-name', target_create[0])
        self.assertIn('--allocated-storage', target_create[0])
        self.assertNotIn('--db-cluster-identifier', target_create[0])
        self.assertIn('DBInstances[0].Endpoint.Address', build)
        target_delete = [b for b in re.findall(r'```bash\n(.*?)```', cleanup, re.S)
                         if 'aws rds delete-db-instance' in b and '$TARGET_DB_ID' in b]
        self.assertEqual(len(target_delete), 1)
        self.assertIn('--no-skip-final-snapshot', target_delete[0])
        self.assertIn('--final-db-snapshot-identifier', target_delete[0])
        for path in (ROOT / 'docs').rglob('*.md'):
            for block in re.findall(r'```[^\n]*\n(.*?)```', path.read_text(), re.S):
                self.assertNotIn('aurora-postgresql', block, str(path))
                self.assertNotIn('AURORA_POSTGRESQL', block, str(path))
                self.assertNotIn('TARGET_WRITER', block, str(path))
                self.assertNotIn('SHOW rds.force_ssl', block, str(path))
        self.assertIn('--engine-name postgres', (ROOT / 'docs/05-dms/build.md').read_text())
        self.assertIn("-vendor: 'POSTGRESQL'", (ROOT / 'docs/04-sct/build.md').read_text())

    def test_download_excludes_runtime_and_state(self):
        with zipfile.ZipFile(ROOT / 'site/downloads/hydra-practice.zip') as archive:
            for name in archive.namelist():
                parts = Path(name).parts
                self.assertNotIn('runtime', parts)
                self.assertNotIn('evidence', parts)
                self.assertNotIn('.env', parts)
                self.assertNotIn('.terraform', parts)
                self.assertNotIn('terraform.tfvars', parts)
                self.assertNotIn('.tfstate', name)


if __name__ == '__main__':
    unittest.main()
