import unittest
import datetime
from unittest.mock import patch
import build

class CoverageTests(unittest.TestCase):
    def test_unreadable_source_is_unknown_not_zero_and_empty_read_is_distinct(self):
        for rows,status,expected in [([], 'AI CEO board not readable with the build token (HTTP 404); not published.', 'unavailable'),([], '0 rows read', 'empty'),([{'url':'safe'}], '1 rows read', 'available')]:
            with patch.object(build,'rows',return_value=[]),patch.object(build,'aiceo_rows',return_value=(rows,status)):
                result=build.snapshot()['aiceo_coverage']
            self.assertEqual(result['state'],expected)
            self.assertEqual(result['exhaustive'],expected!='unavailable')
            self.assertEqual(result['public_rows'],None if expected=='unavailable' else len(rows))
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
    def snap(self,reports,tasks=()):
        calls=[]
        def fake(k,body=None,limit=None):
            calls.append((k,limit,body))
            if k=='checkins':return reports
            if k=='tasks':return list(tasks)
            if k=='agents':return [{'url':'dash'},{'url':'grok'}]
            return []
        with patch.object(build,'rows',side_effect=fake),patch.object(build,'aiceo_rows',return_value=([],'0 rows read')):s=build.snapshot()
        return s,calls
    def test_snapshot_queries_complete_history_before_capping_feed(self):
        reports=[dict(self.report(i),**{'Doing now':f'step {i}'}) for i in range(210)]+[self.report('grok','grok','2026-10-02T23:10:00Z','2026-10-02T23:09:00Z')]
        s,calls=self.snap(reports)
        self.assertIn(('checkins',None),[c[:2] for c in calls]);self.assertEqual(len(s['checkins']),200);self.assertEqual(s['report_coverage']['unique_rows'],211)
        self.assertEqual(s['report_coverage']['collapsed_repeats'],0);self.assertEqual(s['counts']['checkins'],211)
    def test_repeated_heartbeats_collapse_so_other_agents_stay_in_the_feed(self):
        flood=[dict(self.report(i,logged=f'2026-10-04T20:{59-i//10:02d}:{59-i%10:02d}Z'),**{'Doing now':'  Heartbeat OK ','Status':'working'}) for i in range(210)]
        reports=flood+[self.report('grok','grok','2026-10-02T23:10:00Z','2026-10-02T23:09:00Z')]
        s,_=self.snap(reports)
        feed=s['checkins'];self.assertEqual([r['url'] for r in feed],['0','grok'])
        self.assertEqual(feed[0]['_repeats'],210);self.assertEqual(feed[0]['_first_logged'],flood[-1]['Logged'])
        self.assertEqual(s['report_coverage']['collapsed_repeats'],209);self.assertEqual(s['counts']['checkins'],211)
        self.assertEqual(s['counts']['checkins_feed_rows'],2)
        self.assertNotIn('_repeats',s['report_coverage']['per_agent']['dash']['latest'])
    def test_collapse_only_merges_consecutive_identical_reports(self):
        rows=[{'url':'a','Agent':['x'],'Doing now':'one','Status':'WORKING'},{'url':'b','Agent':['y'],'Doing now':'one','Status':'WORKING'},
              {'url':'c','Agent':['x'],'Doing now':'ONE','Status':'working'},{'url':'d','Agent':['x'],'Doing now':'two','Status':'WORKING'},
              {'url':'e','Agent':['x'],'Doing now':'one','Status':'WORKING'},{'url':'f','Agent':None,'Doing now':'one'},{'url':'g','Agent':None,'Doing now':'one'}]
        out=build.collapse_heartbeats(rows)
        self.assertEqual([r['url'] for r in out],['a','b','d','e','f','g']);self.assertEqual(out[0]['_repeats'],2)
    def test_tasks_are_read_in_full_and_done_rows_are_not_published(self):
        tasks=[{'url':str(i),'Status':st} for i,st in enumerate(['🟢 Done','Done','🔴 Needs help','🟡 Moving',None]*30)]
        s,calls=self.snap([self.report('r')],tasks)
        self.assertIn(('tasks',None,None),calls)
        self.assertEqual(s['counts']['tasks_total'],150);self.assertEqual(s['counts']['tasks_open'],90);self.assertEqual(len(s['tasks']),90)
        self.assertEqual(s['counts']['agents'],2)
    def test_extra_private_properties_never_appear_in_coverage(self):
        page={'id':'row','properties':{'Agent':{'type':'relation','relation':[{'id':'dash'}]},'Private':{'type':'rich_text','rich_text':[{'plain_text':'PRIVATE_SENTINEL'}]}}}
        with patch.object(build,'q',return_value=[page]):public=build.rows('checkins')
        _,c=self.coverage(public);self.assertNotIn('PRIVATE_SENTINEL',str(c));self.assertNotIn('Private',str(c))
    def test_invalid_logged_is_quarantined_without_suppressing_valid_latest(self):
        records=[self.report('valid'),self.report('future',logged='2026-10-05T03:00:00Z'),self.report('invalid',logged='bad')]
        cutoff=datetime.datetime(2026,10,4,21,tzinfo=datetime.timezone.utc)
        _,c=build.report_coverage(records,[{'url':'dash'}],[],[],cutoff)
        seat=c['per_agent']['dash'];self.assertEqual(seat['latest']['url'],'valid')
        self.assertEqual(seat['invalid_receipt_rows'],2);self.assertEqual(seat['latest_invalid_receipt']['url'],'future')
    def test_truncated_agent_relation_blocks_exhaustive_absence(self):
        page={'id':'row','properties':{'Agent':{'type':'relation','relation':[{'id':'dash'}],'has_more':True}}}
        with patch.object(build,'q',return_value=[page]):public=build.rows('checkins')
        _,c=self.coverage(public);self.assertFalse(c['exhaustive'])
        self.assertFalse(c['per_agent']['absent']['exhaustive']);self.assertEqual(c['truncated_agent_relation_rows'],1)

if __name__=='__main__':unittest.main()
