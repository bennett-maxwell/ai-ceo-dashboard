import unittest
from unittest.mock import patch
import build

class CoverageTests(unittest.TestCase):
    def report(self,i,agent='dash',logged='2026-10-04T20:59:30Z',time='2026-10-04T20:59:00Z'):
        return {'url':str(i),'Agent':[agent],'Device':['device'],'Project':None,'Logged':logged,'Time':time}
    def coverage(self,reports):
        return build.report_coverage(reports,[{'url':'dash'},{'url':'grok'},{'url':'absent'}],[{'url':'device'}],[])
    def test_latest_per_seat_survives_activity_cap_and_replay_dedup(self):
        reports=[self.report(i) for i in range(210)]+[self.report('grok','grok','2026-10-02T23:10:00Z','2026-10-02T23:09:00Z')]
        reports.append(reports[0])
        feed,c=self.coverage(reports)
        self.assertNotIn('grok',{r['url'] for r in feed[:200]})
        self.assertEqual(c['per_agent']['grok']['latest']['url'],'grok')
        self.assertEqual(c['per_agent']['grok']['matching_rows'],1)
        self.assertEqual(c['per_agent']['absent']['matching_rows'],0)
        self.assertTrue(c['exhaustive']);self.assertEqual(c['duplicate_row_ids'],1)
        self.assertEqual(len(feed),211)
    def test_new_receipt_replaying_old_worker_time_is_flagged(self):
        reports=[self.report('old',logged='2026-10-04T20:58:30Z',time='2026-10-04T20:58:00Z'),self.report('new',time='2026-10-04T20:58:00Z')]
        self.assertTrue(self.coverage(reports)[1]['per_agent']['dash']['latest_replayed'])
    def test_bad_future_old_worker_time_does_not_poison_new_valid_report(self):
        reports=[self.report('old',logged='2026-10-04T20:58:30Z',time='2026-10-05T02:58:00Z'),self.report('new')]
        self.assertFalse(self.coverage(reports)[1]['per_agent']['dash']['latest_replayed'])
    def test_missing_links_explicit_and_primary_ids_not_name_inferred(self):
        r=self.report('missing');r['Agent']=None;r['Device']=['unknown'];r['Project']=['unknown']
        _,c=self.coverage([r]);self.assertEqual(c['unlinked_rows'],1);self.assertEqual(c['unknown_device_links'],1);self.assertEqual(c['unknown_project_links'],1)
        self.assertEqual(len(build.PRIMARY_AGENT_IDS),6);self.assertNotIn('3edcf5514fd381c18e9ad31f16369f38',build.PRIMARY_AGENT_IDS)
        self.assertNotIn('3edcf5514fd3811ebc43c50933e8a73b',build.PRIMARY_AGENT_IDS)
    def test_snapshot_queries_complete_history_before_capping_feed(self):
        reports=[self.report(i) for i in range(210)]+[self.report('grok','grok','2026-10-02T23:10:00Z','2026-10-02T23:09:00Z')]
        calls=[]
        def fake(k,body=None,limit=None):
            calls.append((k,limit))
            if k=='checkins':return reports
            return []
        with patch.object(build,'rows',side_effect=fake):s=build.snapshot()
        self.assertIn(('checkins',None),calls);self.assertEqual(len(s['checkins']),200);self.assertEqual(s['report_coverage']['unique_rows'],211)
    def test_extra_private_properties_never_appear_in_coverage(self):
        page={'id':'row','properties':{'Agent':{'type':'relation','relation':[{'id':'dash'}]},'Private':{'type':'rich_text','rich_text':[{'plain_text':'SECRET_SENTINEL'}]}}}
        with patch.object(build,'q',return_value=[page]):public=build.rows('checkins')
        _,c=self.coverage(public);self.assertNotIn('SECRET_SENTINEL',str(c));self.assertNotIn('Private',str(c))

if __name__=='__main__':unittest.main()
