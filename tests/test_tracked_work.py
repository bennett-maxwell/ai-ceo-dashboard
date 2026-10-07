import datetime
import json
import unittest
import build

NOW=datetime.datetime(2026,10,7,23,0,tzinfo=datetime.timezone.utc)
PROJECT={'url':build.OWNED_WORK_PROJECT,'Progress %':25,'Status':'WORKING','_edited':'2026-10-07T22:50:00Z','Project':'CEO clock-in repair','Company':None,'Doing now':'LEAD_SENTINEL','Proof':'PRIVATE_SENTINEL','Blocker question':'CONTACT_SENTINEL','Device':'DEVICE_SENTINEL'}
REPORT={'url':build.OWNED_WORK_CHECKIN,'Agent':[build.OWNED_WORK_AGENT],'Project':[build.OWNED_WORK_PROJECT],'Logged':'2026-10-07T22:55:00Z','Status':'WORKING','Doing now':'LEAD_SENTINEL','Proof':'PRIVATE_SENTINEL','Device':['DEVICE_SENTINEL'],'Blocker question':'CONTACT_SENTINEL'}
class TrackedWorkTests(unittest.TestCase):
 def test_source_progress_changes_and_output_allowlist(self):
  first=build.owned_work_projection([PROJECT],[REPORT],NOW)
  changed=dict(PROJECT,**{'Progress %':40})
  second=build.owned_work_projection([changed],[REPORT],NOW)
  self.assertEqual((first['progress'],second['progress']),(25,40))
  self.assertEqual(first['as_of'],PROJECT['_edited']); self.assertEqual(first['freshness'],'FRESH')
  self.assertEqual(first['checkin_state'],'MATCHED')
  blob=json.dumps(first)
  for secret in ('LEAD_SENTINEL','PRIVATE_SENTINEL','CONTACT_SENTINEL','DEVICE_SENTINEL',build.OWNED_WORK_AGENT,build.OWNED_WORK_PROJECT,build.OWNED_WORK_CHECKIN): self.assertNotIn(secret,blob)
 def test_missing_or_bad_progress_is_unknown_not_zero(self):
  for value in (None,-1,101,True):
   p=build.owned_work_projection([dict(PROJECT,**{'Progress %':value})],[REPORT],NOW)
   self.assertIsNone(p['progress']); self.assertEqual(p['progress_state'],'UNKNOWN')
 def test_bad_relation_or_checkin_mismatch_is_unknown(self):
  bad=dict(REPORT,Agent=['other'])
  self.assertEqual(build.owned_work_projection([PROJECT],[bad],NOW)['checkin_state'],'UNKNOWN')
  bad=dict(REPORT,Project=['other'])
  self.assertEqual(build.owned_work_projection([PROJECT],[bad],NOW)['checkin_state'],'UNKNOWN')
  bad=dict(REPORT,url='other')
  self.assertEqual(build.owned_work_projection([PROJECT],[bad],NOW)['checkin_state'],'UNKNOWN')
  self.assertEqual(build.owned_work_projection([dict(PROJECT,url='other')],[REPORT],NOW)['progress_state'],'UNKNOWN')
 def test_stale_source_not_build_timestamp(self):
  old=dict(PROJECT,_edited='2026-10-06T22:00:00Z')
  p=build.owned_work_projection([old],[REPORT],NOW)
  self.assertEqual(p['freshness'],'STALE'); self.assertEqual(p['as_of'],old['_edited'])
  missing=dict(PROJECT); missing.pop('_edited')
  self.assertEqual(build.owned_work_projection([missing],[REPORT],NOW)['freshness'],'UNKNOWN')
 def test_template_has_owned_work_panel_not_raw_task_fields(self):
  html=build.render({'tracked_work':build.owned_work_projection([PROJECT],[REPORT],NOW)},'2026-10-07T23:00:00Z')
  self.assertIn('Source progress:',html); self.assertIn('source as-of',html)
  self.assertIn('S.data.tracked_work',html)
  for secret in ('LEAD_SENTINEL','PRIVATE_SENTINEL','CONTACT_SENTINEL','DEVICE_SENTINEL'): self.assertNotIn(secret,html)
if __name__=='__main__': unittest.main()
