"""Publish only the operational fields already displayed by the public dashboard."""
import datetime
import json
import os
from pathlib import Path
import urllib.request

DB = {"agents":"ceaee3c46bcb463891ea1c86e20bdf17","devices":"255af22f85d840709836a5187f407482","projects":"10edde1f306545a3bbfdb9f507d532ed","checkins":"d322e38bf5054e9a965d8696723d596e","crons":"1effc590f7824467bf114ac164d5cc0c","caio":"64223bb0677a4eb3bda557ebeb5b2579","fat20":"a0c83122aaa0410a8acc0b4a889b01f2","coceo":"96f47983f50d44e3bff55404c876e2e9","tasks":"1a757d42a2ae4cb3acdf7e2eff2e0841"}
PUBLIC_FIELDS = {
    "agents": ("Agent", "Status", "Platform", "Role", "Device", "Projects"),
    "devices": ("Device", "Type"),
    "projects": ("Project", "Company", "Status", "Progress %", "Last %", "Finish condition"),
    "checkins": ("Agent", "Logged", "Status", "Doing now", "Project", "Proof", "Device", "Blocker question"),
    "crons": ("Routine", "State", "Cadence", "Runs on", "Defined in"),
    "caio": ("Division", "Status", "Covers", "Projects", "Order"),
    "fat20": ("Rank", "Item", "Status", "Progress %"),
    "coceo": ("Logged", "Author", "Entry", "Type", "Strategy note", "Audit verdict", "Audit of partner"),
    "tasks": ("Focus", "Name", "Owner", "Status", "Progress %"),
}

def q(i, body, limit=None):
    out, cur = [], None
    while True:
        size = min(100, limit - len(out)) if limit else 100
        b = dict(body, page_size=size, **({"start_cursor": cur} if cur else {}))
        r = urllib.request.Request(
            f"https://api.notion.com/v1/databases/{i}/query", json.dumps(b).encode(),
            {"Authorization": f"Bearer {os.environ['NOTION_TOKEN']}",
             "Notion-Version": "2022-06-28", "Content-Type": "application/json"})
        with urllib.request.urlopen(r, timeout=30) as response:
            d = json.load(response)
        out.extend(d["results"])
        if not d.get("has_more") or (limit and len(out) >= limit):
            return out[:limit] if limit else out
        next_cur = d.get("next_cursor")
        if not next_cur or next_cur == cur:
            raise ValueError("Notion pagination did not advance")
        cur = next_cur

def val(p):
    t = p["type"]
    v = p.get(t)
    if t in ("title", "rich_text"):
        return "".join(x["plain_text"] for x in v) or None
    if t == "select": return v and v["name"]
    if t == "relation": return [x["id"].replace("-", "") for x in v]
    if t == "date": return v and v["start"]
    if t == "checkbox": return "__YES__" if v else "__NO__"
    if t in ("number", "url", "created_time"): return v

def rows(k, body=None, limit=None):
    res = []
    for pg in q(DB[k], body or {}, limit):
        props = pg["properties"]
        r = {"url": pg["id"].replace("-", "")}
        for name in PUBLIC_FIELDS[k]:
            r[name] = val(props[name]) if name in props else None
        res.append(r)
    return res

def snapshot():
    new = {"sorts": [{"timestamp": "created_time", "direction": "descending"}]}
    snap = {k: rows(k) for k in DB if k not in ("checkins", "tasks", "coceo")}
    snap["checkins"] = rows("checkins", new, 200)
    snap["coceo"] = rows("coceo", new, 60)
    snap["tasks"] = rows("tasks", {"filter": {"property": "Status", "select": {"does_not_equal": "🟢 Done"}}}, 80)
    return snap

def render(snap, at):
    data = json.dumps(snap, ensure_ascii=False).replace("</", "<\\/")
    return Path("template.html").read_text().replace("__SNAP__", data).replace("__AT__", at)

def main():
    snap = snapshot()
    at = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    site = Path("site")
    site.mkdir(exist_ok=True)
    (site / "index.html").write_text(render(snap, at))
    (site / "version.json").write_text(json.dumps({"built_at": at}))
    print("built", {k: len(v) for k, v in snap.items()}, "at", at)

if __name__ == "__main__":
    main()
