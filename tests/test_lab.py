import datetime
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


class Cursor:
    def __init__(self, rows): self.rows = rows
    def fetchmany(self, n):
        values, self.rows = self.rows[:n], self.rows[n:]
        return values


class MigrationChecks(unittest.TestCase):
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
