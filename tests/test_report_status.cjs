const {test}=require('node:test');
const assert=require('node:assert/strict');
const status=require('../report_status.js');
const NOW=Date.parse('2026-10-04T21:00:00Z');
function coverage(overrides={}){return {agent_id:'agent',included:true,exhaustive:true,matching_rows:1,latest_replayed:false,latest:{url:'row',Agent:['agent'],Logged:'2026-10-04T20:59:30Z',Time:'2026-10-04T20:59:00Z'},...overrides}}
function check(c=coverage(),at='2026-10-04T21:00:00Z'){return status.evaluate(c,at,NOW)}
test('good worker report is recent evidence, never runtime proof',()=>{
 const r=check();assert.equal(r.workerFresh,true);assert.equal(r.receiptRecent,true);assert.match(r.process,/Unknown/);assert.doesNotMatch(r.label,/alive|dead/i);
});
test('late worker with recent receipt stays stale',()=>{
 const c=coverage();c.latest.Time='2026-10-04T20:55:00Z';const r=check(c);assert.equal(r.workerFresh,false);assert.equal(r.receiptRecent,true);assert.match(r.worker,/Stale/);
});
test('future worker Time is quarantined independently of recent receipt',()=>{
 const c=coverage();c.latest.Time='2026-10-05T02:59:00Z';const r=check(c);assert.equal(r.workerFresh,false);assert.equal(r.receiptRecent,true);assert.match(r.worker,/future.*unverified/);
});
test('worker Time future relative to receipt remains invalid after clock catches up',()=>{
 const c=coverage();c.latest.Logged='2026-10-04T20:58:00Z';c.latest.Time='2026-10-04T20:59:00Z';assert.match(check(c).worker,/future/);
});
test('missing, date-only, invalid calendar and future server time cannot validate',()=>{
 for(const t of [null,'garbage','2026-10-04','2026-02-30T20:59:00Z']){const c=coverage();c.latest.Time=t;assert.equal(check(c).workerFresh,false)}
 const c=coverage();c.latest.Logged='2026-10-05T20:59:00Z';const r=check(c);assert.equal(r.receiptRecent,false);assert.equal(r.workerFresh,false);
});
test('replay is unverified even with recent receipt and worker timestamps',()=>{
 const r=check(coverage({latest_replayed:true}));assert.equal(r.receiptRecent,true);assert.equal(r.workerFresh,false);assert.match(r.label,/Replayed/);
});
test('stale/invalid/future snapshot prevents current counters and status claims',()=>{
 for(const at of ['2026-10-04T19:30:35Z','invalid','2026-10-05T21:00:00Z']){
  const r=check(coverage(),at);assert.equal(r.workerFresh,false);assert.equal(r.receiptRecent,false);assert.match(r.label,/Live status unavailable/);
 }
});
test('absence labels distinguish incomplete coverage from exhaustive zero',()=>{
 assert.match(check(null).label,/Not included/);
 assert.match(check(coverage({exhaustive:false,latest:null})).label,/Not included/);
 assert.match(check(coverage({latest:null,matching_rows:0})).label,/Never observed as of exhaustive/);
 assert.match(check(coverage({latest:null,matching_rows:0}),'2026-10-04T19:00:00Z').label,/Live status unavailable/);
});
test('three-minute boundary and exact agent binding are enforced',()=>{
 const c=coverage();c.latest.Time='2026-10-04T20:57:00Z';assert.equal(check(c).workerFresh,true);
 c.latest.Time='2026-10-04T20:56:59Z';assert.equal(check(c).workerFresh,false);
 c.latest.Time='2026-10-04T20:59:00Z';c.latest.Agent=['wrong-agent'];assert.equal(check(c).workerFresh,false);assert.match(check(c).worker,/binding/);
});
test('both always-allow and always-block report validators fail the acceptance checks',()=>{
 function acceptance(fn){const good=fn(coverage(),'2026-10-04T21:00:00Z',NOW);const c=coverage();c.latest.Time='2026-10-05T02:59:00Z';const bad=fn(c,'2026-10-04T21:00:00Z',NOW);assert.equal(good.workerFresh,true);assert.equal(bad.workerFresh,false)}
 assert.doesNotThrow(()=>acceptance(status.evaluate));
 assert.throws(()=>acceptance(()=>({workerFresh:true})));
 assert.throws(()=>acceptance(()=>({workerFresh:false})));
});
