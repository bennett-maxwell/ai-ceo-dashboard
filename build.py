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
    "checkins": ("Agent", "Logged", "Time", "Status", "Doing now", "Project", "Proof", "Device", "Blocker question"),
    "crons": ("Routine", "State", "Cadence", "Runs on", "Defined in"),
    "caio": ("Division", "Status", "Covers", "Projects", "Order"),
    "fat20": ("Rank", "Item", "Status", "Progress %"),
    "coceo": ("Logged", "Author", "Entry", "Type", "Strategy note", "Audit verdict", "Audit of partner"),
    "tasks": ("Focus", "Name", "Owner", "Status", "Progress %"),
}

def q(i, body, limit=None):
    out, cur, seen_cursors = [], None, set()
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
        if not next_cur or next_cur in seen_cursors:
            raise ValueError("Notion pagination did not advance")
        seen_cursors.add(next_cur)
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

PRIMARY_AGENT_IDS = (
    "3edcf5514fd3812ea137d3ce41dafab3", "3edcf5514fd381d7a91dd8a7bdcccb87",
    "3edcf5514fd3816fb3a2cc308727bde6", "3edcf5514fd38131bd00e1080bf6d826",
    "3edcf5514fd381759f9bee1cfade7819", "3edcf5514fd381ecb7a7f9c2f8411b1d",
)

def timestamp(value):
    if not isinstance(value, str) or "T" not in value:
        return None
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else None
    except ValueError:
        return None

def report_coverage(reports, agents, devices, projects):
    # Scan to exhaustion before limiting the activity feed. Never infer absence from a cap.
    unique = {r["url"]: r for r in reports}
    source_rows = sorted(unique.values(), key=lambda r: (timestamp(r.get("Logged")) or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc), r["url"]), reverse=True)
    known_agents = {a["url"] for a in agents}
    known_devices = {d["url"] for d in devices}
    known_projects = {p["url"] for p in projects}
    per_agent = {}
    for agent_id in known_agents | set(PRIMARY_AGENT_IDS):
        linked = [r for r in source_rows if agent_id in (r.get("Agent") or [])]
        latest = linked[0] if linked else None
        valid_older = [timestamp(r.get("Time")) for r in linked[1:]
                       if timestamp(r.get("Time")) is not None and timestamp(r.get("Logged")) is not None
                       and timestamp(r.get("Time")) <= timestamp(r.get("Logged"))]
        worker_time = timestamp(latest.get("Time")) if latest else None
        latest_replayed = bool(worker_time and valid_older and worker_time <= max(valid_older))
        per_agent[agent_id] = {"agent_id": agent_id, "included": agent_id in known_agents,
                               "exhaustive": True, "matching_rows": len(linked),
                               "latest": latest, "latest_replayed": latest_replayed}
    return source_rows, {"source": DB["checkins"], "exhaustive": True,
                         "rows_scanned": len(reports), "unique_rows": len(unique),
                         "duplicate_row_ids": len(reports)-len(unique),
                         "unlinked_rows": sum(not r.get("Agent") for r in source_rows),
                         "unknown_agent_links": sum(i not in known_agents for r in source_rows for i in (r.get("Agent") or [])),
                         "unknown_device_links": sum(i not in known_devices for r in source_rows for i in (r.get("Device") or [])),
                         "unknown_project_links": sum(i not in known_projects for r in source_rows for i in (r.get("Project") or [])),
                         "per_agent": per_agent}

def snapshot():
    new = {"sorts": [{"timestamp": "created_time", "direction": "descending"}]}
    snap = {k: rows(k) for k in DB if k not in ("checkins", "tasks", "coceo")}
    all_reports = rows("checkins", new)
    reports, coverage = report_coverage(all_reports, snap["agents"], snap["devices"], snap["projects"])
    snap["checkins"] = reports[:200]
    snap["report_coverage"] = coverage
    snap["primary_agents"] = list(PRIMARY_AGENT_IDS)
    snap["coceo"] = rows("coceo", new, 60)
    snap["tasks"] = rows("tasks", {"filter": {"property": "Status", "select": {"does_not_equal": "🟢 Done"}}}, 80)
    return snap

def render(snap, at):
    data = json.dumps(snap, ensure_ascii=False).replace("</", "<\\/")
    return (Path("template.html").read_text().replace("__REPORT_STATUS__", Path("report_status.js").read_text())
            .replace("__AT__", at).replace("__SNAP__", data))

def main():
    snap = snapshot()
    at = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    site = Path("site")
    site.mkdir(exist_ok=True)
    (site / "index.html").write_text(render(snap, at))
    (site / "version.json").write_text(json.dumps({"built_at": at}))
    print("built", {k: len(v) for k, v in snap.items() if isinstance(v, list)}, "at", at)

if __name__ == "__main__":
    main()
