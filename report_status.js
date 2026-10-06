(function(root){
 "use strict";
 // Publication age is separate from the six-minute check-in-since-build window.
 const WORKER_MAX_AGE_MS=6*60000,SNAPSHOT_MAX_AGE_MS=30*60000,SILENT_MAX_AGE_MS=24*3600000;
 const WINDOW_MIN=WORKER_MAX_AGE_MS/60000;
 // Every non-retired agent lands in exactly one bucket, so the bucket counts always add up to the total.
 const BUCKETS=["fresh","blocked","clocked","late","never","unverified","unknown"];
 const CLOCK_OUT=/CLOCK(?:ED)?[\s_-]?OUT/i;
 function time(value){
  if(typeof value!=="string")return null;
  const m=value.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})$/);
  if(!m||+m[2]<1||+m[2]>12||+m[3]<1||+m[3]>new Date(Date.UTC(+m[1],+m[2],0)).getUTCDate()||+m[4]>23||+m[5]>59||+(m[6]||0)>59)return null;
  const t=Date.parse(value);return Number.isFinite(t)?t:null;
 }
 function snapshot(at,now=Date.now()){
  const built=time(at),age=built==null?null:now-built;
  const available=age!=null&&age>=0&&age<=SNAPSHOT_MAX_AGE_MS;
  return {available,evidenceAvailable:available,age,built};
 }
 function boundToSeat(last,coverage){
  if(coverage?.matched_by==="title"||last?._matched_by==="title")return true;
  if(Array.isArray(last?.Agent)&&coverage?.agent_id&&last.Agent.includes(coverage.agent_id))return true;
  const title=String(last?.["Check-in"]||"");
  return (coverage?.aliases||[]).some(name=>{
   const n=String(name||"").trim().toLowerCase();
   const t=title.trim().toLowerCase();
   return n&&t.startsWith(n)&&(t.length===n.length||!/[a-z0-9]/i.test(t.charAt(n.length)));
  });
 }
 function evaluate(coverage,builtAt,now=Date.now()){
  const last=coverage?.latest||null,view=snapshot(builtAt,now);
  const result={last,process:"Unknown — no runtime proof",cls:"",color:"var(--gray)",label:"Not included — coverage unknown",workerFresh:false,receiptRecent:false,worker:"Unverified",receipt:"Unknown",coverage:coverage||null,bucket:"unknown",clockedOut:false,silent:false};
  if(!coverage?.included||coverage.exhaustive!==true)return result;
  if(!last){
   if(!view.available){result.label="Live status unavailable — stale or invalid snapshot";return result}
   result.label=coverage.invalid_receipt_rows?"Only invalid server receipts — unverified":"Never observed as of exhaustive snapshot query";
   result.bucket=coverage.invalid_receipt_rows?"unverified":"never";
   return result;
  }
  const logged=time(last.Logged),clock=view.built;
  const validLogged=logged!=null&&clock!=null&&logged<=clock&&logged<=now;
  result.clockedOut=CLOCK_OUT.test(String(last.Status||""));
  result.receipt=validLogged?(clock-logged<=WORKER_MAX_AGE_MS?"Recent server receipt":"Old server receipt"):"Invalid server receipt";
  result.receiptRecent=view.available&&validLogged&&clock-logged<=WORKER_MAX_AGE_MS;
  let problem=null;
  if(!validLogged)problem="Invalid Logged timestamp";
  else if(!boundToSeat(last,coverage))problem="Agent binding unverified";
  if(problem){result.worker=problem;result.label=problem;result.cls="y";result.color="var(--yellow)";result.bucket="unverified"}
  else{
   const age=clock-logged;result.silent=age>SILENT_MAX_AGE_MS;
   if(age<=WORKER_MAX_AGE_MS){result.worker="Check-in since last build (≤"+WINDOW_MIN+"m)";result.workerFresh=view.available;result.label=result.worker;result.cls=view.available?"g":"";result.color=view.available?"var(--green)":"var(--gray)"}
   else{result.worker="No check-in since last build (>"+WINDOW_MIN+"m)";result.label=result.worker;result.cls="y";result.color="var(--yellow)"}
   // A clock-out only excuses silence for a day; after that the agent counts as late like everyone else.
   if(result.clockedOut&&!result.silent){result.bucket="clocked";result.label="Clocked out (reported) · "+result.worker;result.cls="";result.color="var(--gray)"}
   else if(age>WORKER_MAX_AGE_MS){result.bucket="late";if(result.silent){result.label="Silent >24h · "+result.worker;result.cls="r";result.color="var(--red)"}}
   else result.bucket=String(last.Status||"").toUpperCase()==="BLOCKED"?"blocked":"fresh";
  }
  if(!view.available){result.label="Live status unavailable — stale or invalid snapshot";result.workerFresh=false;result.receiptRecent=false;result.cls="";result.color="var(--gray)";result.bucket="unknown"}
  return result;
 }
 function tally(list){
  const counts={total:0};BUCKETS.forEach(b=>counts[b]=0);
  (list||[]).forEach(L=>{counts.total++;counts[BUCKETS.includes(L?.bucket)?L.bucket:"unknown"]++});
  return counts;
 }
 function seatRank(L){
  if(L?.bucket==="fresh"||L?.bucket==="blocked")return 0;
  if(L?.bucket==="late"||L?.bucket==="clocked"||L?.bucket==="unverified")return 1;
  return 2;
 }
 const api={time,snapshot,evaluate,tally,seatRank,boundToSeat,BUCKETS,WORKER_MAX_AGE_MS,SNAPSHOT_MAX_AGE_MS,SILENT_MAX_AGE_MS,WINDOW_MIN};
 if(typeof module!=="undefined"&&module.exports)module.exports=api;else root.ReportStatus=api;
})(globalThis);
