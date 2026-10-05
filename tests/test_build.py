import io
import json
import os
import unittest
from unittest.mock import patch
import urllib.error
import build

class BuildTests(unittest.TestCase):
    def test_allowlist_blocks_private_extras_in_rendered_html(self):
        page = {"id":"12345678-1234-1234-1234-123456789abc", "properties":{
            "Project":{"type":"title","title":[{"plain_text":"Visible </script>"}]},
            "Private note":{"type":"rich_text","rich_text":[{"plain_text":"PRIVATE_SENTINEL"}]},
            "Progress %":{"type":"number","number":None}}}
        with patch.object(build, 'q', return_value=[page]):
            row = build.rows('projects')[0]
        self.assertEqual(set(row), {'url', *build.PUBLIC_FIELDS['projects']})
        self.assertEqual(row['url'], '12345678123412341234123456789abc')
        self.assertIsNone(row['Status'])
        self.assertIsNone(row['Progress %'])
        html = build.render({'projects':[row]}, '2026-10-04T19:00:00Z')
        self.assertNotIn('PRIVATE_SENTINEL', html)
        self.assertNotIn('Private note', html)
        self.assertIn('Visible <\\/script>', html)
        for tab in ('now','coceo','agents','devices','projects','tasks','caio','crons'):
            self.assertIn(f'<section id="{tab}">', html)
        self.assertIn('<meta name="robots" content="noindex, nofollow">', html)
    def test_all_tables_have_explicit_allowlists(self):
        self.assertEqual(set(build.DB), set(build.PUBLIC_FIELDS))
    def test_every_board_maps_to_a_dash_stripped_data_source(self):
        self.assertEqual(set(build.DATA_SOURCES), set(build.DB) | {'aiceo'})
        for i in list(build.DATA_SOURCES.values()) + list(build.DB.values()) + [build.AICEO_DB]:
            self.assertRegex(i, r'^[0-9a-f]{32}$')
        self.assertEqual(build.DATA_SOURCES['aiceo'], '536e453290b74a5083be86567bb46f4c')
    def test_aiceo_board_publishes_no_titles_money_or_links(self):
        page = {"id":"aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "properties":{
            "Name":{"type":"title","title":[{"plain_text":"PRIVATE_TITLE"}]},
            "$ at stake":{"type":"number","number":12345},
            "Proof Link":{"type":"url","url":"https://example.invalid/private"},
            "Type":{"type":"select","select":{"name":"Plan"}},
            "Status":{"type":"select","select":{"name":"Open"}},
            "date:Date:start":{"type":"date","date":{"start":"2026-10-05"}}}}
        with patch.object(build, 'q', return_value=[page]) as called:
            rows, status = build.aiceo_rows()
        self.assertEqual(called.call_args.kwargs['route'], 'data_sources')
        self.assertEqual(called.call_args.kwargs['version'], '2025-09-03')
        self.assertEqual(set(rows[0]), {'url','Type','Status','Seat','Graded by','Date'})
        self.assertEqual(rows[0]['Date'], '2026-10-05')
        self.assertNotIn('PRIVATE_TITLE', json.dumps(rows)); self.assertNotIn('12345', json.dumps(rows))
        self.assertEqual(status, '1 rows read')
    def test_aiceo_board_unreadable_never_breaks_the_build(self):
        err = urllib.error.HTTPError('fixture', 404, 'Not found', {}, None)
        with patch.object(build, 'q', side_effect=[err, urllib.error.HTTPError('fixture', 403, 'Forbidden', {}, None)]):
            rows, status = build.aiceo_rows()
        self.assertEqual(rows, []); self.assertIn('HTTP 403', status)
    def test_query_route_and_version_are_explicit(self):
        page = dict(results=[1], has_more=False)
        with patch.dict(os.environ, NOTION_TOKEN='synthetic'), patch.object(build.urllib.request,'urlopen',return_value=io.BytesIO(json.dumps(page).encode())) as opened:
            build.q('fixture', {}, route='data_sources', version='2025-09-03')
        req = opened.call_args.args[0]
        self.assertTrue(req.full_url.endswith('/v1/data_sources/fixture/query'))
        self.assertEqual(req.get_header('Notion-version'), '2025-09-03')

    def test_pagination_complete_and_timeout(self):
        pages = [dict(results=[1],has_more=True,next_cursor='next'), dict(results=[2],has_more=False)]
        with patch.dict(os.environ, NOTION_TOKEN='synthetic'), patch.object(build.urllib.request,'urlopen',side_effect=[io.BytesIO(json.dumps(p).encode()) for p in pages]) as opened:
            self.assertEqual(build.q('fixture',{}),[1,2])
        self.assertEqual(opened.call_args.kwargs['timeout'],30)
        self.assertEqual(json.loads(opened.call_args.args[0].data)['start_cursor'],'next')
    def test_repeated_cursor_fails(self):
        page=dict(results=[1],has_more=True,next_cursor='next')
        with patch.dict(os.environ,NOTION_TOKEN='synthetic'), patch.object(build.urllib.request,'urlopen',side_effect=[io.BytesIO(json.dumps(page).encode()) for _ in range(2)]):
            with self.assertRaisesRegex(ValueError,'did not advance'): build.q('fixture',{})
    def test_http_error_fails_without_partial_snapshot(self):
        with patch.dict(os.environ,NOTION_TOKEN='synthetic'), patch.object(build.urllib.request,'urlopen',side_effect=urllib.error.HTTPError('fixture',401,'Unauthorized',{},None)):
            with self.assertRaises(urllib.error.HTTPError): build.q('fixture',{})
    def test_limits_request_only_needed_rows(self):
        page=dict(results=list(range(60)),has_more=True,next_cursor='next')
        with patch.dict(os.environ,NOTION_TOKEN='synthetic'), patch.object(build.urllib.request,'urlopen',return_value=io.BytesIO(json.dumps(page).encode())) as opened:
            self.assertEqual(len(build.q('fixture',{},60)),60)
        self.assertEqual(json.loads(opened.call_args.args[0].data)['page_size'],60)

class ScrubTests(unittest.TestCase):
    def test_contacts_tokens_and_env_terms_are_scrubbed_but_ids_kept(self):
        tok = 'gh' + 'p_' + 'A' * 24
        snap = {'agents': [{'url': '3edcf5514fd381d7a91dd8a7bdcccb87', 'Role': 'Call lead at (555) 201-3344 or 5552013344, mail a.b@example.com',
                            'Doing now': 'Pasted ' + tok + ' by mistake', 'Proof': 'https://github.com/o/r/actions/runs/18234567890',
                            'Logged': '2026-10-05T14:07:00.000Z', 'Progress %': 40, 'Note': 'about Zebra Matter today'}]}
        with patch.dict(os.environ, {'SCRUB_TERMS': 'zebra matter\n,  ,xy'}, clear=False):
            terms = build.scrub_terms()
            out, hits = build.scrub(snap)
        self.assertEqual(terms, ['zebra matter'])
        row = out['agents'][0]; text = json.dumps(out)
        self.assertEqual(row['url'], '3edcf5514fd381d7a91dd8a7bdcccb87')
        self.assertNotIn('201-3344', text); self.assertNotIn('5552013344', text); self.assertNotIn('example.com', text)
        self.assertNotIn(tok, text); self.assertNotIn('Zebra', text)
        self.assertIn('[private]', row['Note']); self.assertIn('[redacted token]', row['Doing now'])
        self.assertEqual(row['Proof'], 'https://github.com/o/r/actions/runs/18234567890')
        self.assertEqual(row['Logged'], '2026-10-05T14:07:00.000Z'); self.assertEqual(row['Progress %'], 40)
        self.assertEqual(hits, 5)
        self.assertEqual(snap['agents'][0]['Note'], 'about Zebra Matter today')
    def test_missing_terms_only_fail_when_required(self):
        with patch.dict(os.environ, {'SCRUB_TERMS': '', 'REQUIRE_SCRUB_TERMS': '1'}, clear=False):
            os.environ.pop('SCRUB_TERMS_FILE', None)
            with self.assertRaises(SystemExit): build.scrub_terms()
        with patch.dict(os.environ, {'SCRUB_TERMS': '', 'REQUIRE_SCRUB_TERMS': '0'}, clear=False):
            self.assertEqual(build.scrub_terms(), [])
    def test_terms_file_is_read_when_named(self):
        import tempfile
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as f:
            f.write('Quokka Case\n')
        try:
            with patch.dict(os.environ, {'SCRUB_TERMS': '', 'SCRUB_TERMS_FILE': f.name}, clear=False):
                out, hits = build.scrub({'x': 'the quokka case file'})
            self.assertEqual(out['x'], 'the [private] file'); self.assertEqual(hits, 1)
        finally:
            os.unlink(f.name)

if __name__=='__main__': unittest.main()
