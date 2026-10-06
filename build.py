"""Publish only the operational fields already displayed by the public dashboard."""
import datetime
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

DB = {"agents":"ceaee3c46bcb463891ea1c86e20bdf17","devices":"255af22f85d840709836a5187f407482","projects":"10edde1f306545a3bbfdb9f507d532ed","checkins":"d322e38bf5054e9a965d8696723d596e","crons":"1effc590f7824467bf114ac164d5cc0c","caio":"64223bb0677a4eb3bda557ebeb5b2579","fat20":"a0c83122aaa0410a8acc0b4a889b01f2","coceo":"96f47983f50d44e3bff55404c876e2e9","tasks":"1a757d42a2ae4cb3acdf7e2eff2e0841"}
# Notion data source behind each database id (Command Center HUB 3edcf5514fd38180b7b5e780b12bcccc).
# Tasks sit under page 3e4cf5514fd381b497f7e6aab1521c82. All ids are dash-stripped.
DATA_SOURCES = {
    "agents": "a2ee467b26574173b36edf538f6e35e3",
    "devices": "d691854b83d449e8aac13b991805c239",
    "projects": "2c75f5446d7c42eaa33f55747167624e",
    "checkins": "adb5ca487d474f4e8ca72b449c91fa41",
    "crons": "474e80b06e004a0db3738b1b6426696a",
    "caio": "8f7f298cd6a84508adae96207c4d8d4c",
    "fat20": "277b8c966cf041c7ab271917fd2044bb",
    "coceo": "c1880491d8e743218fbc5299db8dfd5f",
    "tasks": "e706e6d10f18481e998118c873469d87",
    "aiceo": "536e453290b74a5083be86567bb46f4c",
}
# The AI CEO board is read through its data source; its database id is the fallback route.
AICEO_DB = "fe2ecada96c74adfb196753abc4dfb12"
# Row titles, dollar amounts and proof links on the AI CEO board are internal (customer names, cash figures),
# so only these select/date fields are ever published from it.
AICEO_FIELDS = ("Type", "Status", "Seat", "Graded by", "date:Date:start")
PUBLIC_FIELDS = {
    "agents": ("Agent", "Status", "Platform", "Role", "Device", "Projects"),
    "devices": ("Device", "Type"),
    "projects": ("Project", "Company", "Status", "Progress %", "Last %", "Finish condition"),
    "checkins": ("Check-in", "Agent", "Logged", "Time", "Status", "Doing now", "Project", "Proof", "Device", "Blocker question"),
    "crons": ("Routine", "State", "Cadence", "Runs on", "Defined in"),
    "caio": ("Division", "Status", "Covers", "Projects", "Order"),
    "fat20": ("Rank", "Item", "Status", "Progress %"),
    "coceo": ("Logged", "Author", "Entry", "Type", "Strategy note", "Audit verdict", "Audit of partner"),
    "tasks": ("Focus", "Name", "Owner", "Status", "Progress %"),
}

def notion_id(i, route="databases"):
    """data_sources (2025-09-03) 404s on dash-stripped ids; keep other routes as the caller sent them."""
    raw = str(i).replace("-", "")
    if route == "data_sources" and re.fullmatch(r"[0-9a-f]{32}", raw):
        return f"{raw[:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:]}"
    return i

def q(i, body, limit=None, route="databases", version="2022-06-28"):
    out, cur, seen_cursors = [], None, set()
    while True:
        size = min(100, limit - len(out)) if limit else 100
        b = dict(body, page_size=size, **({"start_cursor": cur} if cur else {}))
        r = urllib.request.Request(
            f"https://api.notion.com/v1/{route}/{notion_id(i, route)}/query", json.dumps(b).encode(),
            {"Authorization": f"Bearer {os.environ['NOTION_TOKEN']}",
             "Notion-Version": version, "Content-Type": "application/json"})
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
        if k == "checkins" and props.get("Agent", {}).get("has_more"):
            r["_agent_relation_complete"] = False
        res.append(r)
    return res

# Current seats, in board order. Aliases are title prefixes (case-insensitive).
PRIMARY_AGENTS = (
    ("3edcf5514fd381659d38cbb6d9a1a51a", ("Rocky",)),
    ("3edcf5514fd38108b4f4e2d2e319ebe2", ("Leo",)),
    ("3edcf5514fd381c18e9ad31f16369f38", ("Dot",)),
    ("3edcf5514fd3815aa780ca4aff45c771", ("Hank",)),
    ("3edcf5514fd3812ea137d3ce41dafab3", ("Dash",)),
    ("3edcf5514fd381d7a91dd8a7bdcccb87", ("Mack CLI", "Mack")),
)
PRIMARY_AGENT_IDS = tuple(agent_id for agent_id, _names in PRIMARY_AGENTS)
PRIMARY_AGENT_ALIASES = {agent_id: names for agent_id, names in PRIMARY_AGENTS}
ACCEPT_RE = re.compile(r"\bACCEPT\b", re.I)

def timestamp(value):
    if not isinstance(value, str) or "T" not in value:
        return None
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else None
    except ValueError:
        return None

def title_prefix_match(title, name):
    text = str(title or "").strip().lower()
    prefix = str(name or "").strip().lower()
    if not text or not prefix:
        return False
    return text.startswith(prefix) and (len(text) == len(prefix) or not text[len(prefix)].isalnum())

def aliases_for(agent_id, agents):
    names = list(PRIMARY_AGENT_ALIASES.get(agent_id, ()))
    for agent in agents:
        if agent.get("url") == agent_id and agent.get("Agent"):
            names.append(agent["Agent"])
            break
    out, seen = [], set()
    for name in names:
        key = name.lower()
        if key not in seen:
            seen.add(key)
            out.append(name)
    return out

def row_matches_agent(row, agent_id, names):
    if agent_id in (row.get("Agent") or []):
        return "relation"
    title = row.get("Check-in")
    for name in names:
        if title_prefix_match(title, name):
            return "title"
    return None

def report_identity(row):
    agents = tuple(sorted(row.get("Agent") or []))
    if agents:
        return agents
    title = str(row.get("Check-in") or "").strip().lower()
    head = re.split(r"\s*[·\-|/]\s*", title, 1)[0].strip()
    return ("title:" + (head or row.get("url") or ""),)

def is_finished_status(status):
    return re.sub(r"^[^A-Za-z]+", "", str(status or "")).strip().upper() == "FINISHED"

def is_approval_row(row):
    return any(ACCEPT_RE.search(str(row.get(field) or "")) for field in ("Status", "Doing now", "Check-in"))

def row_seats(row, agents=()):
    seats = set(row.get("Agent") or [])
    title = row.get("Check-in")
    for agent_id in set(PRIMARY_AGENT_IDS) | {a.get("url") for a in agents if a.get("url")}:
        names = aliases_for(agent_id, agents)
        if any(title_prefix_match(title, name) for name in names):
            seats.add(agent_id)
    return seats

def finish_label(row, source_rows_desc, agents=()):
    if not is_finished_status(row.get("Status")):
        return None
    seats = row_seats(row, agents)
    row_time = timestamp(row.get("Logged"))
    for other in source_rows_desc:
        if other.get("url") == row.get("url") or not is_approval_row(other):
            continue
        other_seats = row_seats(other, agents)
        other_time = timestamp(other.get("Logged"))
        if other_seats and seats and other_seats.isdisjoint(seats) and other_time and row_time and other_time >= row_time:
            return "accepted"
    return "self-reported"

def needs_bennett_rows(source_rows_desc, agents=()):
    out, seen = [], set()
    for row in source_rows_desc:
        blocker = str(row.get("Blocker question") or "").strip()
        approval = is_approval_row(row)
        if (not blocker and not approval) or row["url"] in seen:
            continue
        seen.add(row["url"])
        item = dict(row)
        item["need"] = "blocker" if blocker else "approval"
        if is_finished_status(row.get("Status")):
            item["_finish"] = finish_label(row, source_rows_desc, agents)
        out.append(item)
    return out[:40]

def report_coverage(reports, agents, devices, projects, cutoff=None):
    # Scan to exhaustion before limiting the activity feed. Never infer absence from a cap.
    unique = {r["url"]: r for r in reports}
    source_rows = sorted(unique.values(), key=lambda r: (timestamp(r.get("Logged")) or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc), r["url"]), reverse=True)
    cutoff = cutoff or datetime.datetime.now(datetime.timezone.utc)
    complete = all(r.get("_agent_relation_complete", True) for r in source_rows)
    known_agents = {a["url"] for a in agents}
    known_devices = {d["url"] for d in devices}
    known_projects = {p["url"] for p in projects}
    per_agent = {}
    for agent_id in known_agents | set(PRIMARY_AGENT_IDS):
        names = aliases_for(agent_id, agents)
        linked, how = [], {}
        for row in source_rows:
            matched = row_matches_agent(row, agent_id, names)
            if matched:
                linked.append(row)
                how[row["url"]] = matched
        valid = [r for r in linked if timestamp(r.get("Logged")) is not None and timestamp(r["Logged"]) <= cutoff]
        invalid = [r for r in linked if r not in valid]
        latest = valid[0] if valid else None
        valid_older = [timestamp(r.get("Time")) for r in valid[1:]
                       if timestamp(r.get("Time")) is not None and timestamp(r.get("Logged")) is not None
                       and timestamp(r.get("Time")) <= timestamp(r.get("Logged"))]
        worker_time = timestamp(latest.get("Time")) if latest else None
        latest_replayed = bool(worker_time and valid_older and worker_time <= max(valid_older))
        per_agent[agent_id] = {"agent_id": agent_id, "included": agent_id in known_agents,
                               "exhaustive": complete, "matching_rows": len(linked),
                               "invalid_receipt_rows": len(invalid), "latest_invalid_receipt": invalid[0] if invalid else None,
                               "latest": latest, "latest_replayed": latest_replayed,
                               "matched_by": how.get(latest["url"]) if latest else None,
                               "aliases": names}
    return source_rows, {"source": DB["checkins"], "exhaustive": complete,
                         "receipt_cutoff": cutoff.isoformat().replace("+00:00", "Z"),
                         "truncated_agent_relation_rows": sum(r.get("_agent_relation_complete") is False for r in source_rows),
                         "rows_scanned": len(reports), "unique_rows": len(unique),
                         "duplicate_row_ids": len(reports)-len(unique),
                         "unlinked_rows": sum(not r.get("Agent") for r in source_rows),
                         "unknown_agent_links": sum(i not in known_agents for r in source_rows for i in (r.get("Agent") or [])),
                         "unknown_device_links": sum(i not in known_devices for r in source_rows for i in (r.get("Device") or [])),
                         "unknown_project_links": sum(i not in known_projects for r in source_rows for i in (r.get("Project") or [])),
                         "per_agent": per_agent}

def collapse_heartbeats(rows_desc):
    """Fold consecutive identical reports from one agent (same Doing now and Status) into its newest row.

    rows_desc must be newest first. Other agents' rows in between do not break a run, so a 2-minute
    heartbeat flood from one agent cannot crowd every other agent out of the capped feed."""
    out, last_by_agent = [], {}
    for r in rows_desc:
        agent = report_identity(r)
        key = (" ".join(str(r.get("Doing now") or "").split()).lower(), str(r.get("Status") or "").upper())
        prev = last_by_agent.get(agent)
        if agent and agent != ("title:",) and prev is not None and prev[0] == key:
            kept = prev[1]
            kept["_repeats"] = kept.get("_repeats", 1) + 1
            kept["_first_logged"] = r.get("Logged")
            continue
        kept = dict(r)
        out.append(kept)
        last_by_agent[agent] = (key, kept)
    return out

def is_done(status):
    return re.sub(r"^[^A-Za-z]+", "", str(status or "")).strip().lower() == "done"

def source_error(route, error):
    """Only bounded status metadata leaves an HTTP failure; never raw body or message."""
    record = {"route": route, "status": None, "error_code": "transport_error", "request_id": None}
    if not isinstance(error, urllib.error.HTTPError):
        return record
    record["status"] = error.code
    allowed = {"invalid_json", "invalid_request_url", "invalid_request", "validation_error",
               "missing_version", "unauthorized", "restricted_resource", "object_not_found",
               "conflict_error", "rate_limited", "internal_server_error", "bad_gateway",
               "service_unavailable", "database_connection_unavailable", "gateway_timeout"}
    record["error_code"] = "unknown_http_error"
    headers = error.headers or {}
    request_id = headers.get("x-request-id") or headers.get("X-Request-Id")
    try:
        body = json.loads(error.read(4096))
        if isinstance(body, dict):
            if body.get("code") in allowed:
                record["error_code"] = body["code"]
            request_id = request_id or body.get("request_id")
    except (ValueError, OSError, AttributeError, TypeError):
        pass
    finally:
        error.close()
    if isinstance(request_id, str) and re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", request_id):
        record["request_id"] = request_id
    return record

def aiceo_rows(diagnostics=None):
    """Historical Plan/Audit/Run coverage; separate from the current command-center hub."""
    diagnostics = diagnostics if diagnostics is not None else []
    try:
        try:
            pages = q(DATA_SOURCES["aiceo"], {}, route="data_sources", version="2025-09-03")
            diagnostics.append({"route": "data_sources", "status": 200, "error_code": None, "request_id": None})
        except urllib.error.HTTPError as e:
            diagnostics.append(source_error("data_sources", e))
            if e.code not in (400, 404):
                raise
            try:
                pages = q(AICEO_DB, {})
                diagnostics.append({"route": "databases", "status": 200, "error_code": None, "request_id": None})
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as fallback:
                diagnostics.append(source_error("databases", fallback))
                raise
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            diagnostics.append(source_error("data_sources", e))
            raise
    except urllib.error.HTTPError as e:
        return [], f"Historical AI CEO coverage not readable with the build connection (HTTP {e.code}); not published."
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        return [], "Historical AI CEO coverage read failed; not published."
    out = []
    for pg in pages:
        props = pg.get("properties", {})
        r = {"url": pg["id"].replace("-", "")}
        for name in AICEO_FIELDS:
            if name == "date:Date:start":
                p = props.get(name) or props.get("Date")
                r["Date"] = val(p) if p else None
            else:
                r[name] = val(props[name]) if name in props else None
        out.append(r)
    return out, f"{len(out)} rows read"

def snapshot():
    new = {"sorts": [{"timestamp": "created_time", "direction": "descending"}]}
    snap = {k: rows(k) for k in DB if k not in ("checkins", "tasks", "coceo")}
    all_reports = rows("checkins", new)
    reports, coverage = report_coverage(all_reports, snap["agents"], snap["devices"], snap["projects"])
    feed = collapse_heartbeats(reports)
    coverage["collapsed_repeats"] = len(reports) - len(feed)
    labeled = []
    for row in feed[:200]:
        item = dict(row)
        if is_finished_status(item.get("Status")):
            item["_finish"] = finish_label(item, reports, snap["agents"])
        labeled.append(item)
    snap["checkins"] = labeled
    snap["needs_bennett"] = needs_bennett_rows(reports, snap["agents"])
    snap["report_coverage"] = coverage
    snap["primary_agents"] = list(PRIMARY_AGENT_IDS)
    snap["primary_agent_names"] = {i: aliases_for(i, snap["agents"]) for i in PRIMARY_AGENT_IDS}
    snap["coceo"] = rows("coceo", new, 60)
    all_tasks = rows("tasks")
    snap["tasks"] = [t for t in all_tasks if not is_done(t.get("Status"))]
    aiceo_diagnostics = []
    snap["aiceo"], snap["aiceo_status"] = aiceo_rows(aiceo_diagnostics)
    print("historical_aiceo_routes:", json.dumps(aiceo_diagnostics, sort_keys=True))
    aiceo_read = snap["aiceo_status"] == f"{len(snap['aiceo'])} rows read"
    snap["aiceo_coverage"] = {"state": ("available" if snap["aiceo"] else "empty") if aiceo_read else "unavailable",
                              "exhaustive": aiceo_read, "public_rows": len(snap["aiceo"]) if aiceo_read else None}
    snap["counts"] = {"agents": len(snap["agents"]), "tasks_total": len(all_tasks), "tasks_open": len(snap["tasks"]),
                      "checkins": coverage["unique_rows"], "checkins_feed_rows": len(feed), "aiceo": len(snap["aiceo"])}
    return snap

# Public scrub. Protected terms come only from the environment (repo secret SCRUB_TERMS) or a local
# file named by SCRUB_TERMS_FILE; they are never committed. Token prefixes are written as character
# classes so this file itself carries no token-shaped text.
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
# Digits inside URLs, ids and paths (run ids, query values) are not phone numbers, so a run must not touch / = # . or -.
PHONE_RE = re.compile(r"(?<![\w/=#.-])(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?![\w/-])|(?<![\w/=#.+-])\+?1?\d{10}(?![\w/.-])")
TOKEN_RE = re.compile(r"(?:n[t]n_|secre[t]_|gh[po]_|s[k]-|x[o]x[a-z]-)[A-Za-z0-9_-]{8,}")
ID_RE = re.compile(r"[0-9a-f]{32}")

def scrub_terms():
    raw = os.environ.get("SCRUB_TERMS", "")
    path = os.environ.get("SCRUB_TERMS_FILE")
    if path and Path(path).is_file():
        raw += "\n" + Path(path).read_text()
    terms = sorted({t.strip() for t in re.split(r"[\n,]", raw) if len(t.strip()) >= 3}, key=len, reverse=True)
    if not terms and os.environ.get("REQUIRE_SCRUB_TERMS") == "1":
        raise SystemExit("scrub: REQUIRE_SCRUB_TERMS=1 but no terms were loaded")
    return terms

def scrub(snap, terms=None):
    """Return (clean copy, replacement count). Ids stay intact; every other string is scrubbed."""
    terms = scrub_terms() if terms is None else terms
    term_re = re.compile("|".join(re.escape(t) for t in terms), re.IGNORECASE) if terms else None
    hits = 0
    def text(s):
        nonlocal hits
        if ID_RE.fullmatch(s):
            return s
        for rx, repl in ((term_re, "[private]"), (TOKEN_RE, "[redacted token]"),
                         (EMAIL_RE, "[redacted email]"), (PHONE_RE, "[redacted phone]")):
            if rx is not None:
                s, n = rx.subn(repl, s)
                hits += n
        return s
    def walk(v):
        if isinstance(v, str):
            return text(v)
        if isinstance(v, list):
            return [walk(x) for x in v]
        if isinstance(v, dict):
            return {k: walk(x) for k, x in v.items()}
        return v
    return walk(snap), hits

# Rows kept off the public page by Notion page id: public-exclude.txt holds one id per line (dashes optional,
# '#' starts a comment). The Notion rows themselves are untouched. A missing or malformed list stops the build.
EXCLUDE_FILE = "public-exclude.txt"

def norm_id(s):
    return str(s).strip().lower().replace("-", "")

def excluded_ids(path=EXCLUDE_FILE):
    p = Path(path)
    if not p.is_file():
        raise SystemExit(f"exclude: {path} missing; refusing to publish without it")
    ids = {norm_id(line.split("#", 1)[0]) for line in p.read_text().splitlines()} - {""}
    bad = [i for i in ids if not ID_RE.fullmatch(i)]
    if bad:
        raise SystemExit(f"exclude: {len(bad)} malformed id line(s) in {path}")
    return ids

def exclude(snap, ids):
    """Return (copy without listed rows, dropped row count). A list item whose url is listed is dropped from
    every section, a listed id in a relation list is removed, a dict value pointing at a listed row becomes None,
    and any other mention of a listed id (dashed or not) is replaced, so no listed id reaches the page."""
    if not ids:
        return snap, 0
    id_re = re.compile("|".join(f"{i[:8]}-?{i[8:12]}-?{i[12:16]}-?{i[16:20]}-?{i[20:]}" for i in sorted(ids)), re.IGNORECASE)
    dropped = 0
    def listed(v):
        if isinstance(v, dict):
            return norm_id(v.get("url") or "") in ids
        return isinstance(v, str) and norm_id(v) in ids
    def walk(v):
        nonlocal dropped
        if isinstance(v, str):
            return id_re.sub("[excluded]", v)
        if isinstance(v, list):
            dropped += sum(isinstance(x, dict) and listed(x) for x in v)
            return [walk(x) for x in v if not listed(x)]
        if isinstance(v, dict):
            return {walk(k): (None if listed(x) else walk(x)) for k, x in v.items() if not listed(k)}
        return v
    return walk(snap), dropped

def render(snap, at):
    data = json.dumps(snap, ensure_ascii=False).replace("</", "<\\/")
    return (Path("template.html").read_text().replace("__REPORT_STATUS__", Path("report_status.js").read_text())
            .replace("__AT__", at).replace("__SNAP__", data))

def main():
    terms, ids = scrub_terms(), excluded_ids()
    snap, dropped = exclude(snapshot(), ids)
    print(f"exclude: ids={len(ids)} dropped={dropped}")
    snap, hits = scrub(snap, terms)
    print(f"scrub: terms_loaded={len(terms)} replaced={hits}")
    at = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    site = Path("site")
    site.mkdir(exist_ok=True)
    (site / "index.html").write_text(render(snap, at))
    (site / "version.json").write_text(json.dumps({"built_at": at}))
    print("built", {k: len(v) for k, v in snap.items() if isinstance(v, list)}, "counts", snap["counts"], "aiceo:", snap["aiceo_status"], "at", at)

if __name__ == "__main__":
    main()
