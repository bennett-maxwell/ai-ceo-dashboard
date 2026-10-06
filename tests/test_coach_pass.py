"""Tests for scripts/coach_pass.py with a mocked Notion API (no network, no token)."""
import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import coach_pass as cp  # noqa: E402

NOW = dt.datetime(2026, 10, 6, 4, 30, tzinfo=dt.timezone.utc)
MACK_ID = "3edcf5514fd381d7a91dd8a7bdcccb87"


def title(s):
    return {"type": "title", "title": [{"plain_text": s}]}


def sel(s):
    return {"type": "select", "select": {"name": s} if s else None}


def rel(*ids):
    return {"type": "relation", "relation": [{"id": i} for i in ids]}


def agent_row(aid, name, status):
    return {"id": aid, "properties": {"Agent": title(name), "Status": sel(status)}}


def checkin(aid, minutes_ago=2):
    return {"id": "c" + aid, "created_time": (NOW - dt.timedelta(minutes=minutes_ago)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "properties": {"Agent": rel(aid), "Check-in": title("row"), "Status": sel("WORKING"),
                           "Project": rel("p1"), "Device": rel("d1"),
                           "Proof": {"type": "url", "url": "https://example.org/x"},
                           "Trail key": {"type": "rich_text", "rich_text": [{"plain_text": "k"}]}}}


def coach_row(aid, minutes_ago, n=1):
    return {"id": "x" + aid, "created_time": (NOW - dt.timedelta(minutes=minutes_ago)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "properties": {"Entry": title("COACH · seat · 21:27 MT · pass #%d" % n), "Dispatched to": rel(aid)}}


class FakeAPI:
    def __init__(self, agents, checkins=(), coach=()):
        self.agents, self.checkins, self.coach = list(agents), list(checkins), list(coach)
        self.posts = []

    def __call__(self, method, path, body=None):
        if path == "data_sources/%s/query" % cp.DS_AGENTS:
            return {"results": self.agents, "has_more": False}
        if path == "data_sources/%s/query" % cp.DS_CHECKINS:
            return {"results": self.checkins, "has_more": False}
        if path == "data_sources/%s/query" % cp.DS_COCEO:
            return {"results": self.coach, "has_more": False}
        if method == "POST" and path == "pages":
            self.posts.append(body)
            return {"id": "new-%d" % len(self.posts)}
        raise AssertionError("unexpected call %s %s" % (method, path))


def live_agents(**override):
    rows = []
    for s in cp.SEATS:
        rows.append(agent_row(s["agent"], s["seat"], override.get(s["seat"], "🟢 Alive")))
    return rows


def recipients(api):
    return [b["properties"]["Dispatched to"]["relation"][0]["id"] for b in api.posts]


class CoachPassTests(unittest.TestCase):
    def test_all_six_live_seats_get_one_row_with_five_lines(self):
        api = FakeAPI(live_agents(), [checkin(s["agent"]) for s in cp.SEATS])
        cp.run(NOW, api, log=lambda m: None)
        self.assertEqual(len(api.posts), 6)
        for b in api.posts:
            note = "".join(x["text"]["content"] for x in b["properties"]["Strategy note"]["rich_text"])
            lines = note.split("\n")
            self.assertTrue(lines[0].startswith("COACH · "))
            self.assertEqual([l.split(":")[0] for l in lines[1:]], ["LAST", "NOW", "IMPROVE", "PROOF DUE", "NEXT"])
            self.assertEqual(b["properties"]["Type"]["select"]["name"], "DISPATCH")

    def test_retired_and_inactive_seats_are_excluded(self):
        api = FakeAPI(live_agents(**{"Dot": "⛔ Retired", "Grok Web": "Inactive"}))
        cp.run(NOW, api, log=lambda m: None)
        sent = recipients(api)
        self.assertEqual(len(sent), 4)
        self.assertNotIn(cp.norm("3edcf5514fd381c18e9ad31f16369f38"), sent)  # Dot
        self.assertNotIn(cp.norm("3f1cf5514fd38132b072c4e7cc220cff"), sent)  # Grok Web

    def test_mack_is_never_a_recipient_even_if_listed(self):
        seats = cp.SEATS + [{"seat": "Mack CLI", "agent": MACK_ID, "project": "p", "now": "x", "next": "y"},
                            {"seat": "Claude MB CLI", "agent": "aaaa", "project": "p", "now": "x", "next": "y"}]
        agents = {cp.norm(s["agent"]): (s["seat"], "🟢 Alive") for s in seats}
        kept = cp.eligible_seats(seats, agents)
        self.assertEqual(len(kept), 6)
        self.assertNotIn(MACK_ID, [cp.norm(s["agent"]) for s in kept])
        orig = cp.SEATS
        try:
            cp.SEATS = seats
            api = FakeAPI([agent_row(s["agent"], s["seat"], "🟢 Alive") for s in seats])
            cp.run(NOW, api, log=lambda m: None)
        finally:
            cp.SEATS = orig
        self.assertNotIn(MACK_ID, recipients(api))
        self.assertEqual(len(api.posts), 6)

    def test_dedupe_skips_seat_coached_in_last_8_minutes(self):
        dash = cp.SEATS[0]["agent"]
        dot = cp.SEATS[1]["agent"]
        api = FakeAPI(live_agents(), coach=[coach_row(dash, 3, 4), coach_row(dot, 9, 4)])
        cp.run(NOW, api, log=lambda m: None)
        sent = recipients(api)
        self.assertNotIn(cp.norm(dash), sent)
        self.assertIn(cp.norm(dot), sent)
        self.assertEqual(len(sent), 5)

    def test_pass_number_follows_existing_coach_rows(self):
        api = FakeAPI(live_agents(), coach=[coach_row("zz", 30, 7)])
        cp.run(NOW, api, log=lambda m: None)
        self.assertTrue(all("pass #8" in b["properties"]["Entry"]["title"][0]["text"]["content"] for b in api.posts))

    def test_missed_seat_gets_missed_line_and_smaller_now(self):
        api = FakeAPI(live_agents())
        cp.run(NOW, api, log=lambda m: None)
        note = api.posts[0]["properties"]["Strategy note"]["rich_text"][0]["text"]["content"]
        self.assertIn("LAST: MISSED", note)
        self.assertIn("NOW: smallest shippable piece of", note)

    def test_stops_at_deadline(self):
        api = FakeAPI(live_agents())
        logs = []
        out = cp.run(cp.STOP_AT, api, log=logs.append)
        self.assertEqual(out, [])
        self.assertEqual(api.posts, [])
        self.assertIn("stop time", logs[0])

    def test_dry_run_writes_nothing(self):
        api = FakeAPI(live_agents())
        out = cp.run(NOW, api, dry_run=True, log=lambda m: None)
        self.assertEqual(len(out), 6)
        self.assertEqual(api.posts, [])


if __name__ == "__main__":
    unittest.main()
