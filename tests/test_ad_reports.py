import datetime
import json
import tempfile
import unittest

import build

AT = datetime.datetime(2026, 10, 8, 18, 0, tzinfo=datetime.timezone.utc)
ROWS = [{"url": "a" * 32, "Brand": "SH", "Week start": "2026-09-28", "Spend": 1174.82, "Leads": 126, "CPL": 9.32,
         "Pull time": "2026-10-07T19:16:00.000Z"},
        {"url": "b" * 32, "Brand": "SH", "Week start": "2026-09-21", "Spend": 1186.34, "Leads": 112, "CPL": 10.59,
         "Pull time": "2026-10-07T19:16:00.000Z"}]
SRC = {"rows": ROWS, "status": "2 rows read"}


class AdReportsTest(unittest.TestCase):
    def test_last_two_full_weeks(self):
        self.assertEqual(build.ad_weeks(AT), ["2026-09-28", "2026-09-21"])

    def test_every_brand_week_is_listed_and_figures_withheld_by_default(self):
        out = build.ad_reports_projection(SRC, AT, False)
        self.assertEqual(len(out["cells"]), 12)
        self.assertEqual(out["filed"], 2)
        self.assertEqual(out["brands"], [f"Brand {i}" for i in range(1, 7)])
        text = json.dumps(out)
        for secret in ("SH", "Indy Clover", "1174.82", "126", "9.32"):
            self.assertNotIn(secret, text)

    def test_figures_and_names_only_when_published(self):
        out = build.ad_reports_projection(SRC, AT, True)
        sh = [c for c in out["cells"] if c["brand"] == "SH"]
        self.assertEqual([c["spend"] for c in sh], [1174.82, 1186.34])
        self.assertEqual(sum(c["filed"] for c in out["cells"] if c["brand"] != "SH"), 0)

    def test_publish_flag_must_be_exactly_true(self):
        for body, want in (('{"publish_figures": true}', True), ('{"publish_figures": "yes"}', False), ("[]", False), ("x", False)):
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
                f.write(body)
            self.assertIs(build.load_ad_publish(f.name), want)
        self.assertFalse(build.load_ad_publish("ad_reports_public.json"))

    def test_public_html_carries_no_ad_figures_while_unpublished(self):
        snap = {"ad_reports": dict(SRC, publish=False), "ad_reports_at": "2026-10-08T18:00:00Z"}
        html = build.render(snap, "2026-10-08T18:00:00Z")
        self.assertIn("Ad Reports", html)
        self.assertNotIn("1174.82", html)
        self.assertIn('"filed": 2', html)


if __name__ == "__main__":
    unittest.main()
