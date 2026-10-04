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
            "Private secret":{"type":"rich_text","rich_text":[{"plain_text":"SECRET_SENTINEL"}]},
            "Progress %":{"type":"number","number":None}}}
        with patch.object(build, 'q', return_value=[page]):
            row = build.rows('projects')[0]
        self.assertEqual(set(row), {'url', *build.PUBLIC_FIELDS['projects']})
        self.assertEqual(row['url'], '12345678123412341234123456789abc')
        self.assertIsNone(row['Status'])
        self.assertIsNone(row['Progress %'])
        html = build.render({'projects':[row]}, '2026-10-04T19:00:00Z')
        self.assertNotIn('SECRET_SENTINEL', html)
        self.assertNotIn('Private secret', html)
        self.assertIn('Visible <\\/script>', html)
        for tab in ('now','coceo','agents','devices','projects','tasks','caio','crons'):
            self.assertIn(f'<section id="{tab}">', html)
    def test_all_tables_have_explicit_allowlists(self):
        self.assertEqual(set(build.DB), set(build.PUBLIC_FIELDS))
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

if __name__=='__main__': unittest.main()
