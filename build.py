import json,os,urllib.request,datetime
T=os.environ["NOTION_TOKEN"]
DB={"agents":"ceaee3c46bcb463891ea1c86e20bdf17","devices":"255af22f85d840709836a5187f407482","projects":"10edde1f306545a3bbfdb9f507d532ed","checkins":"d322e38bf5054e9a965d8696723d596e","crons":"1effc590f7824467bf114ac164d5cc0c","caio":"64223bb0677a4eb3bda557ebeb5b2579","fat20":"a0c83122aaa0410a8acc0b4a889b01f2","coceo":"96f47983f50d44e3bff55404c876e2e9","tasks":"1a757d42a2ae4cb3acdf7e2eff2e0841"}
def q(i,body):
    out=[];cur=None
    while True:
        b=dict(body,page_size=100,**({"start_cursor":cur} if cur else {}))
        r=urllib.request.Request(f"https://api.notion.com/v1/databases/{i}/query",json.dumps(b).encode(),{"Authorization":f"Bearer {T}","Notion-Version":"2022-06-28","Content-Type":"application/json"})
        d=json.load(urllib.request.urlopen(r));out+=d["results"]
        if not d.get("has_more") or len(out)>=400: return out
        cur=d["next_cursor"]
def val(p):
    t=p["type"];v=p.get(t)
    if t in("title","rich_text"): return "".join(x["plain_text"] for x in v) or None
    if t=="select": return v and v["name"]
    if t=="relation": return [x["id"].replace("-","") for x in v]
    if t=="date": return v and v["start"]
    if t=="checkbox": return "__YES__" if v else "__NO__"
    if t in("number","url","created_time"): return v
def rows(k,body={}):
    res=[]
    for pg in q(DB[k],body):
        r={"url":pg["id"].replace("-","")}
        for n,p in pg["properties"].items(): r[n]=val(p)
        res.append(r)
    return res
new={"sorts":[{"timestamp":"created_time","direction":"descending"}]}
snap={k:rows(k) for k in DB if k not in("checkins","tasks","coceo")}
snap["checkins"]=rows("checkins",new)[:200];snap["coceo"]=rows("coceo",new)[:60]
snap["tasks"]=rows("tasks",{"filter":{"property":"Status","select":{"does_not_equal":"🟢 Done"}}})[:80]
mt=datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(hours=6)
h=open("template.html").read().replace("__SNAP__",json.dumps(snap,ensure_ascii=False).replace("</","<\\/")).replace("__AT__",mt.strftime("%b %-d, %-I:%M %p MT"))
os.makedirs("site",exist_ok=True);open("site/index.html","w").write(h);print("built",{k:len(v) for k,v in snap.items()})
