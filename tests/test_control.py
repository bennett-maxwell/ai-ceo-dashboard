import json, tempfile, unittest
from pathlib import Path
import build

class ControlTest(unittest.TestCase):
    def test_missing_or_bad_file_gives_empty_note(self):
        self.assertEqual(build.load_control("/no/such/file.json"), {"note": ""})
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write("not json")
        self.assertEqual(build.load_control(f.name), {"note": ""})

    def test_note_is_trimmed_and_capped(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"note": "  " + "x" * 500 + "  "}, f)
        self.assertEqual(len(build.load_control(f.name)["note"]), build.NOTE_MAX)

    def test_note_is_escaped(self):
        out = build.note_html("<script>alert(1)</script>")
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)

    def test_empty_note_renders_nothing(self):
        self.assertEqual(build.note_html(""), "")

    def test_repo_control_file_is_small_and_valid(self):
        p = Path("control.json")
        self.assertLess(p.stat().st_size, 1024)
        self.assertIn("note", json.loads(p.read_text()))

    def test_render_shows_build_stamp_and_note(self):
        out = build.render({"projects": []}, "2026-10-08T15:30:00Z", {"note": "Voice test"}, "abcdef1234")
        self.assertIn("built 2026-10-08T15:30:00Z · abcdef1", out)
        self.assertIn("Voice test", out)
        self.assertNotIn("__BUILT__", out)
        self.assertNotIn("__NOTE__", out)

if __name__ == "__main__":
    unittest.main()
