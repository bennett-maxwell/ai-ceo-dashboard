(function(root){
 "use strict";
 // Publication age is separate from the three-minute worker evidence window.
 const WORKER_MAX_AGE_MS=3*60000,SNAPSHOT_MAX_AGE_MS=30*60000,SILENT_MAX_AGE_MS=24*3600000;
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
  return {available:age!=null&&age>=0&&age<=SNAPSHOT_MAX_AGE_MS,evidenceAvailable:age!=null&&age>=0&&age<=WORKER_MAX_AGE_MS,age,built};
 }
 function evaluate(coverage,builtAt,now=Date.now()){
  const last=coverage?.latest||null,view=snapshot(builtAt,now);
  const result={last,process:"Unknown — no runtime proof",cls:"",color:"var(--gray)",label:"Not included — coverage unknown",workerFresh:false,receiptRecent:false,worker:"Unverified",receipt:"Unknown",coverage:coverage||null,bucket:"unknown",clockedOut:false,silent:false};
  if(!coverage?.included||coverage.exhaustive!==true)return result;
  if(!last){
   if(!view.evidenceAvailable){result.label="Live status unavailable — stale or invalid snapshot";return result}
   result.label=coverage.invalid_receipt_rows?"Only invalid server receipts — unverified":"Never observed as of exhaustive snapshot query";
   result.bucket=coverage.invalid_receipt_rows?"unverified":"never";
   return result;
  }
  const logged=time(last.Logged),worker=time(last.Time);
  const validLogged=logged!=null&&logged<=now&&view.built!=null&&logged<=view.built;
  result.clockedOut=CLOCK_OUT.test(String(last.Status||""));
  result.receipt=validLogged?(now-logged<=WORKER_MAX_AGE_MS?"Recent server receipt":"Old server receipt"):"Invalid server receipt";
  result.receiptRecent=view.evidenceAvailable&&validLogged&&now-logged<=WORKER_MAX_AGE_MS;
  let problem=null;
  if(!validLogged)problem="Invalid Logged timestamp";
  else if(!Array.isArray(last.Agent)||!last.Agent.includes(coverage.agent_id))problem="Agent binding unverified";
  else if(worker==null)problem="Worker Time missing or invalid";
  else if(worker>logged||worker>now)problem="Worker Time future — unverified";
  else if(coverage.latest_replayed)problem="Replayed worker Time — unverified";
  if(problem){result.worker=problem;result.label=problem;result.cls="y";result.color="var(--yellow)";result.bucket="unverified"}
  else{
   const age=now-worker;result.silent=age>SILENT_MAX_AGE_MS;
   if(age<=WORKER_MAX_AGE_MS){result.worker="Fresh worker report (≤"+WINDOW_MIN+"m)";result.workerFresh=view.evidenceAvailable;result.label=result.worker;result.cls=view.evidenceAvailable?"g":"";result.color=view.evidenceAvailable?"var(--green)":"var(--gray)"}
   else{result.worker="Stale worker report (>"+WINDOW_MIN+"m)";result.label=result.worker;result.cls="y";result.color="var(--yellow)"}
   // A clock-out only excuses silence for a day; after that the agent counts as late like everyone else.
   if(result.clockedOut&&!result.silent){result.bucket="clocked";result.label="Clocked out (reported) · "+result.worker;result.cls="";result.color="var(--gray)"}
   else if(age>WORKER_MAX_AGE_MS){result.bucket="late";if(result.silent){result.label="Silent >24h · "+result.worker;result.cls="r";result.color="var(--red)"}}
   else result.bucket=String(last.Status||"").toUpperCase()==="BLOCKED"?"blocked":"fresh";
  }
  if(!view.evidenceAvailable){result.label="Live status unavailable — stale or invalid snapshot";result.workerFresh=false;result.receiptRecent=false;result.cls="";result.color="var(--gray)";result.bucket="unknown"}
  return result;
 }
 function tally(list){
  const counts={total:0};BUCKETS.forEach(b=>counts[b]=0);
  (list||[]).forEach(L=>{counts.total++;counts[BUCKETS.includes(L?.bucket)?L.bucket:"unknown"]++});
  return counts;
 }
 const api={time,snapshot,evaluate,tally,BUCKETS,WORKER_MAX_AGE_MS,SNAPSHOT_MAX_AGE_MS,SILENT_MAX_AGE_MS,WINDOW_MIN};
 if(typeof module!=="undefined"&&module.exports)module.exports=api;else root.ReportStatus=api;
})(globalThis);
