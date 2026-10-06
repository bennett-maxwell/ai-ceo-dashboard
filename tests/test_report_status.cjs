const {test}=require('node:test');
const assert=require('node:assert/strict');
const status=require('../report_status.js');
const NOW=Date.parse('2026-10-04T21:00:00Z');
function coverage(overrides={}){return {agent_id:'agent',included:true,exhaustive:true,matching_rows:1,latest_replayed:false,latest:{url:'row',Agent:['agent'],Logged:'2026-10-04T20:59:30Z',Time:'2026-10-04T20:59:00Z'},...overrides}}
function check(c=coverage(),at='2026-10-04T21:00:00Z'){return status.evaluate(c,at,NOW)}
test('good check-in since last build is recent evidence, never runtime proof',()=>{
 const r=check();assert.equal(r.workerFresh,true);assert.equal(r.receiptRecent,true);assert.match(r.process,/Unknown/);assert.doesNotMatch(r.label,/alive|dead/i);assert.match(r.worker,/since last build/);
});
test('old check-in stays late even when worker Time looks new',()=>{
 const c=coverage();c.latest.Logged='2026-10-04T20:50:00Z';c.latest.Time='2026-10-04T20:59:00Z';const r=check(c);assert.equal(r.workerFresh,false);assert.equal(r.receiptRecent,false);assert.match(r.worker,/No check-in since last build/);
});
test('future Logged cannot validate',()=>{
 const c=coverage();c.latest.Logged='2026-10-05T20:59:00Z';const r=check(c);assert.equal(r.receiptRecent,false);assert.equal(r.workerFresh,false);
});
test('missing, date-only and invalid calendar Logged cannot validate',()=>{
 for(const t of [null,'garbage','2026-10-04','2026-02-30T20:59:00Z']){const c=coverage();c.latest.Logged=t;assert.equal(check(c).workerFresh,false)}
});
test('stale/invalid/future snapshot prevents current counters and status claims',()=>{
 for(const at of ['2026-10-04T20:29:59Z','invalid','2026-10-05T21:00:00Z']){
  const r=check(coverage(),at);assert.equal(r.workerFresh,false);assert.equal(r.receiptRecent,false);assert.match(r.label,/Live status unavailable/);
 }
});
test('absence labels distinguish incomplete coverage from exhaustive zero',()=>{
 assert.match(check(null).label,/Not included/);
 assert.match(check(coverage({exhaustive:false,latest:null})).label,/Not included/);
 assert.match(check(coverage({latest:null,matching_rows:0})).label,/Never observed as of exhaustive/);
 assert.match(check(coverage({latest:null,matching_rows:0}),'2026-10-04T20:29:00Z').label,/Live status unavailable/);
});
test('six-minute boundary and title or relation binding are enforced',()=>{
 assert.equal(status.WINDOW_MIN,6);assert.equal(status.SNAPSHOT_MAX_AGE_MS,30*60000);
 const c=coverage();c.latest.Logged='2026-10-04T20:54:00Z';assert.equal(check(c).workerFresh,true);
 c.latest.Logged='2026-10-04T20:53:59.999Z';assert.equal(check(c).workerFresh,false);
 c.latest.Logged='2026-10-04T20:59:00Z';c.latest.Agent=['wrong-agent'];assert.equal(check(c).workerFresh,false);assert.match(check(c).worker,/binding/);
 const titled=coverage({matched_by:'title'});titled.latest.Agent=null;titled.latest['Check-in']='leo · 13:52 MT';titled.aliases=['Leo'];
 assert.equal(check(titled).workerFresh,true);
});
test('both always-allow and always-block report validators fail the acceptance checks',()=>{
 function acceptance(fn){const good=fn(coverage(),'2026-10-04T21:00:00Z',NOW);const c=coverage();c.latest.Logged='2026-10-05T02:59:00Z';const bad=fn(c,'2026-10-04T21:00:00Z',NOW);assert.equal(good.workerFresh,true);assert.equal(bad.workerFresh,false)}
 assert.doesNotThrow(()=>acceptance(status.evaluate));
 assert.throws(()=>acceptance(()=>({workerFresh:true})));
 assert.throws(()=>acceptance(()=>({workerFresh:false})));
});

test('snapshot window is thirty minutes and also gates evidence',()=>{
 assert.equal(status.snapshot('2026-10-04T20:30:00Z',NOW).available,true);
 assert.equal(status.snapshot('2026-10-04T20:29:59Z',NOW).available,false);
 assert.equal(status.snapshot('2026-10-04T20:50:00Z',NOW).evidenceAvailable,true);
 assert.equal(status.snapshot('2026-10-04T20:29:59Z',NOW).evidenceAvailable,false);
});
test('ten-minute-old snapshot can still show check-ins relative to that build',()=>{
 const c=coverage();c.latest.Logged='2026-10-04T20:48:00Z';
 const r=check(c,'2026-10-04T20:50:00Z');assert.equal(r.workerFresh,true);assert.equal(r.bucket,'fresh');
 const late=coverage();late.latest.Logged='2026-10-04T20:40:00Z';
 assert.equal(check(late,'2026-10-04T20:50:00Z').bucket,'late');
});
test('clocked-out agent is excused for a day, then counted late and red',()=>{
 const recent=coverage();recent.latest.Status='Clocked out';recent.latest.Logged='2026-10-04T18:00:30Z';recent.latest.Time='2026-10-04T18:00:00Z';
 const r=check(recent);assert.equal(r.bucket,'clocked');assert.equal(r.clockedOut,true);
 const old=coverage();old.latest.Status='CLOCK-OUT';assert.equal(check(old).clockedOut,true);old.latest.Logged='2026-10-01T21:00:30Z';old.latest.Time='2026-10-01T21:00:00Z';
 const o=check(old);assert.equal(o.bucket,'late');assert.equal(o.cls,'r');assert.match(o.label,/Silent >24h/);
});
test('a long-silent agent can only add to the late count, never lower it',()=>{
 const c=coverage();c.latest.Time='2026-10-04T20:59:00Z';c.latest.Logged='2026-10-04T20:59:30Z';
 const base=Date.parse('2026-10-04T21:00:00Z');let previous=0;
 for(const mins of [1,29,31,120,23*60,25*60,3*1440]){
  const now=base+mins*60000,built=new Date(now).toISOString();
  const late=status.tally([status.evaluate(c,built,now)]).late;
  assert.ok(late>=previous,'late count dropped at +'+mins+'m');previous=late;
  if(mins>30)assert.equal(late,1);
 }
});
test('future Logged is never fresh and lands in unverified',()=>{
 const l=coverage();l.latest.Logged='2026-10-04T21:05:00Z';const b=check(l);assert.equal(b.workerFresh,false);assert.equal(b.bucket,'unverified');
});
test('buckets are exclusive and always add up to the total',()=>{
 const blocked=coverage();blocked.latest.Status='BLOCKED';
 const late=coverage();late.latest.Logged='2026-10-04T20:00:00Z';late.latest.Time='2026-10-04T20:00:00Z';
 const list=[check(),check(blocked),check(late),check(coverage({latest:null,matching_rows:0})),check(coverage({latest:null,invalid_receipt_rows:1})),check(null),check(coverage(),'2026-10-04T20:29:00Z')];
 assert.equal(list[1].bucket,'blocked');
 const t=status.tally(list);assert.equal(t.total,7);
 assert.equal(status.BUCKETS.reduce((n,b)=>n+t[b],0),t.total);
 assert.deepEqual([t.fresh,t.blocked,t.late,t.never,t.unverified,t.unknown],[1,1,1,1,1,2]);
});
test('seat rank is live then late then dead',()=>{
 assert.equal(status.seatRank({bucket:'fresh'}),0);
 assert.equal(status.seatRank({bucket:'blocked'}),0);
 assert.equal(status.seatRank({bucket:'late'}),1);
 assert.equal(status.seatRank({bucket:'never'}),2);
});
