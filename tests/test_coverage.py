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
    def test_same_minute_result_beats_pickup_whatever_the_page_ids(self):
        for pick_id,done_id in [('a','z'),('z','a')]:
            pick=self.report(pick_id,logged='2026-10-06T14:40:00.000Z');pick['Status']='PICKED UP'
            done=self.report(done_id,logged='2026-10-06T14:40:00.000Z');done['Status']='FINISHED'
            self.assertEqual(self.coverage([pick,done])[1]['per_agent']['dash']['latest']['Status'],'FINISHED')
            self.assertEqual(self.coverage([done,pick])[1]['per_agent']['dash']['latest']['Status'],'FINISHED')
        newer_pick=self.report('p',logged='2026-10-06T14:41:00.000Z');newer_pick['Status']='Picked up'
        older_done=self.report('d',logged='2026-10-06T14:40:00.000Z');older_done['Status']='FINISHED'
        self.assertEqual(self.coverage([older_done,newer_pick])[1]['per_agent']['dash']['latest']['url'],'p')
    def test_new_receipt_replaying_old_worker_time_is_flagged(self):
        reports=[self.report('old',logged='2026-10-04T20:58:30Z',time='2026-10-04T20:58:00Z'),self.report('new',time='2026-10-04T20:58:00Z')]
        self.assertTrue(self.coverage(reports)[1]['per_agent']['dash']['latest_replayed'])
    def test_bad_future_old_worker_time_does_not_poison_new_valid_report(self):
        reports=[self.report('old',logged='2026-10-04T20:58:30Z',time='2026-10-05T02:58:00Z'),self.report('new')]
        self.assertFalse(self.coverage(reports)[1]['per_agent']['dash']['latest_replayed'])
    def test_missing_links_explicit_and_primary_ids_not_name_inferred(self):
        r=self.report('missing');r['Agent']=None;r['Device']=['unknown'];r['Project']=['unknown']
        _,c=self.coverage([r]);self.assertEqual(c['unlinked_rows'],1);self.assertEqual(c['unknown_device_links'],1);self.assertEqual(c['unknown_project_links'],1)
        self.assertNotIn('3edcf5514fd3811ebc43c50933e8a73b',build.PRIMARY_AGENT_IDS)
    def test_primary_ids_are_dash_dot_hank_plus_recent_mack_and_never_retired(self):
        # Agents-DB page ids checked 2026-10-06 (Agents data source a2ee467b-2657-4173-b36e-df538f6e35e3).
        dash,dot,hank,mack='3edcf5514fd3812ea137d3ce41dafab3','3edcf5514fd381c18e9ad31f16369f38','3edcf5514fd3815aa780ca4aff45c771','3edcf5514fd381d7a91dd8a7bdcccb87'
        retired={'3edcf5514fd381759f9bee1cfade7819':'Grok ST','3edcf5514fd381659d38cbb6d9a1a51a':'Rocky'}
        self.assertEqual(build.PRIMARY_AGENT_IDS,(dash,dot,hank,mack))
        for rid,name in retired.items():self.assertNotIn(rid,build.PRIMARY_AGENT_IDS,name)
        self.assertEqual(len(set(build.PRIMARY_AGENT_IDS)),len(build.PRIMARY_AGENT_IDS))
        self.assertTrue(all(len(i)==32 and '-' not in i for i in build.PRIMARY_AGENT_IDS))
    def test_picked_up_variants_normalize_for_display_and_counts(self):
        for raw in ['PICKED_UP','PICKED-UP','PICKED','PICKEDUP','PICKED UP','picked up',' Picked_Up ']:
            self.assertEqual(build.norm_status(raw),'PICKED UP',raw)
        for raw in ['WORKING','PICKING','UNPICKED','PICKED UPDATE','',None]:
            self.assertEqual(build.norm_status(raw),raw)
        reports=[{'Status':s} for s in ['PICKED_UP','PICKED_UP','PICKED-UP','PICKED','PICKEDUP','PICKED UP','WORKING',None]]
        self.assertEqual(build.status_counts(reports),{'PICKED UP':6,'No status':1,'WORKING':1})
    def test_rows_normalize_checkin_status_but_not_other_sources(self):
        page={'id':'row','properties':{'Status':{'type':'select','select':{'name':'PICKED_UP'}}}}
        with patch.object(build,'q',return_value=[page]):
            self.assertEqual(build.rows('checkins')[0]['Status'],'PICKED UP')
    def test_project_checkins_use_complete_scan_and_ignore_future_or_bad_logged(self):
        now=datetime.datetime(2026,10,4,21,0,tzinfo=datetime.timezone.utc)
        reports=[{'url':'1','Project':['p1'],'Logged':'2026-10-04T20:30:00Z'},{'url':'2','Project':['p1','p2'],'Logged':'2026-10-04T20:50:00Z'},
                 {'url':'3','Project':['p2'],'Logged':'2026-10-05T03:00:00Z'},{'url':'4','Project':['p3'],'Logged':'bad'},{'url':'5','Project':None,'Logged':'2026-10-04T20:59:00Z'}]
        out=build.project_checkins(reports,now)
        self.assertEqual(out,{'p1':{'latest_logged':'2026-10-04T20:50:00Z','rows':2},'p2':{'latest_logged':'2026-10-04T20:50:00Z','rows':1}})
    def test_snapshot_publishes_project_checkins_and_status_counts_over_all_rows(self):
        reports=[dict(self.report(i),Project=['proj'],Status='PICKED_UP' if i%2 else 'WORKING') for i in range(210)]
        s,_=self.snap(reports)
        self.assertEqual(s['project_checkins']['proj']['rows'],210)
        self.assertEqual(s['counts']['checkin_status'],{'PICKED UP':105,'WORKING':105})
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
