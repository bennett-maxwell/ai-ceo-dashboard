import datetime
import json
import unittest
import build

NOW = datetime.datetime(2026, 10, 7, 23, 50, tzinfo=datetime.timezone.utc)
PROJECT = {'url': build.OWNED_WORK_PROJECT, 'Progress %': 25, 'Status': '🟡 Moving',
           '_edited': '2026-10-07T23:30:00Z', 'Project': 'PRIVATE_PROJECT',
           'Doing now': 'LEAD_SENTINEL', 'Proof': 'PRIVATE_SENTINEL'}
def report(row_id, logged, progress=10, status='🟡 Working', **extra):
    return {'url': row_id, 'Agent': [build.OWNED_WORK_AGENT], 'Project': [build.OWNED_WORK_PROJECT],
            'Logged': logged, 'Progress %': progress, 'Status': status,
            'Doing now': 'LEAD_SENTINEL', 'Proof': 'PRIVATE_SENTINEL', **extra}

class TrackedWorkTests(unittest.TestCase):
 def test_newest_relation_matched_different_id_and_separate_project_progress(self):
  reports = [report('old-row', '2026-10-07T22:54:00Z', 10),
             report('new-row', '2026-10-07T23:39:00Z', 10)]
  result = build.owned_work_projection([PROJECT], reports, NOW)
  self.assertEqual(result['progress'], 10)
  self.assertEqual(result['as_of'], '2026-10-07T23:39:00Z')
  self.assertEqual(result['project_progress'], 25)
  self.assertEqual(result['status'], 'WORKING')
  self.assertEqual(result['project_status'], 'MOVING')
  self.assertTrue(result['mismatch'])
  changed = report('newer-id', '2026-10-07T23:45:00Z', 40)
  next_result = build.owned_work_projection([PROJECT], reports + [changed], NOW)
  self.assertEqual((next_result['progress'], next_result['project_progress']), (40, 25))
  self.assertTrue(next_result['mismatch'])
 def test_newest_invalid_progress_does_not_fall_back(self):
  result = build.owned_work_projection([PROJECT], [report('older', '2026-10-07T23:40:00Z', 10),
                                                    report('newer', '2026-10-07T23:45:00Z', None)], NOW)
  self.assertIsNone(result['progress'])
  self.assertEqual(result['progress_state'], 'UNKNOWN')
  self.assertEqual(result['project_progress'], 25)
 def test_stale_keeps_last_known_report_value_and_project_is_separate(self):
  result = build.owned_work_projection([PROJECT], [report('old', '2026-10-07T23:39:00Z', 10)], NOW)
  self.assertEqual(result['progress'], 10)
  self.assertEqual(result['progress_state'], 'SOURCED')
  self.assertEqual(result['freshness'], 'STALE')
  self.assertEqual(result['project_progress'], 25)
 def test_future_malformed_and_incomplete_relation_never_claim_current(self):
  for logged, extra in [('2026-10-07T23:55:00Z', {}), ('not-a-time', {}),
                        ('2026-10-07T23:39:00Z', {'_agent_relation_complete': False})]:
   with self.subTest(logged=logged):
    result = build.owned_work_projection([PROJECT], [report('candidate', logged, 10, **extra)], NOW)
    self.assertIsNone(result['progress'])
    self.assertEqual(result['checkin_state'], 'UNKNOWN')
    self.assertEqual(result['freshness'], 'UNKNOWN')
 def test_equal_latest_contradictory_reports_are_ambiguous(self):
  rows = [report('one', '2026-10-07T23:45:00Z', 10), report('two', '2026-10-07T23:45:00Z', 20)]
  result = build.owned_work_projection([PROJECT], rows, NOW)
  self.assertIsNone(result['progress'])
  self.assertEqual(result['progress_state'], 'AMBIGUOUS')
  self.assertEqual(result['checkin_state'], 'AMBIGUOUS')
  self.assertEqual(result['freshness'], 'UNKNOWN')
 def test_relations_must_match_exact_agent_and_project(self):
  for extra in ({'Agent': ['other']}, {'Project': ['other']}):
   row = report('bad', '2026-10-07T23:45:00Z', 10)
   row.update(extra)
   result = build.owned_work_projection([PROJECT], [row], NOW)
   self.assertIsNone(result['progress'])
   self.assertEqual(result['checkin_state'], 'UNKNOWN')
 def test_public_render_keeps_values_separate_and_redacts_source_data(self):
  raw = {'tracked_work': build.owned_work_projection([PROJECT], [report('private-row-id', '2026-10-07T23:45:00Z', 40)], NOW)}
  html = build.render(raw, '2026-10-07T23:50:00Z')
  self.assertIn('Current report progress:', html)
  self.assertIn('Project-recorded:', html)
  self.assertIn('Mismatch:', html)
  self.assertIn('MOVING', html)
  self.assertIn('"progress": 40', html)
  self.assertIn('"project_progress": 25', html)
  self.assertNotIn('private-row-id', html)
  for secret in ('LEAD_SENTINEL', 'PRIVATE_SENTINEL', 'PRIVATE_PROJECT', build.OWNED_WORK_AGENT, build.OWNED_WORK_PROJECT):
   self.assertNotIn(secret, html)
  self.assertIsNone(__import__('re').search(r'[0-9a-f]{32}', html, __import__('re').I))

if __name__ == '__main__': unittest.main()
