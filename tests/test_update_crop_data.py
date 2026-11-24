import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import update_crop_data as u  # noqa: E402

PAGE = '''<a href="javascript:filedownload('2018', 'file', '9');" title="첨부파일다운로드">GAP 인증농가 현황_20260318.csv</a>
<a href="javascript:filedownload('2018', 'file', '10');" title="첨부파일다운로드">GAP 인증농가 현황_20260914.csv</a>'''


class T(unittest.TestCase):
    def test_latest_mafra_file(self):
        self.assertEqual(u.latest_mafra_file(PAGE), ("10", "2026-09-14"))

    def test_fetch_failure_keeps_old_files(self):
        def boom(*a, **k):
            raise OSError("network down")
        old = u.http
        u.http = boom
        try:
            with tempfile.TemporaryDirectory() as d:
                path = os.path.join(d, "gap.json")
                with open(path, "w", encoding="utf-8") as f:
                    f.write('{"old": true}')
                self.assertNotEqual(u.main(["x", d]), 0)
                with open(path, encoding="utf-8") as f:
                    self.assertEqual(f.read(), '{"old": true}')
        finally:
            u.http = old

    def test_write_json_skips_when_only_updated_date_differs(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.json")
            u.write_json(path, {"meta": {"updated": "2026-11-01"}, "v": 1})
            self.assertFalse(u.write_json(path, {"meta": {"updated": "2026-11-24"}, "v": 1}))
            with open(path, encoding="utf-8") as f:
                self.assertIn("2026-11-01", f.read())
            self.assertTrue(u.write_json(path, {"meta": {"updated": "2026-11-24"}, "v": 2}))

    def test_fill_missing_phones_keeps_old_numbers(self):
        old = {"by_region": {"경북 청송군": [{"name": "청송군 농업기술센터", "tel": "054-873-2440"}],
                             "경북": [{"name": "경상북도 농업기술원", "tel": "053-320-0200"}]}}
        new = {"by_region": {"경북 청송군": [{"name": "청송군 농업기술센터", "tel": ""}],
                             "경북": [{"name": "경상북도 농업기술원", "tel": "053-111-2222"}],
                             "경북 봉화군": [{"name": "봉화군 농업기술센터", "tel": ""}]}}
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "contacts.json")
            u.write_json(path, old)
            self.assertEqual(u.fill_missing_phones(path, new), 1)
        self.assertEqual(new["by_region"]["경북 청송군"][0]["tel"], "054-873-2440")
        self.assertEqual(new["by_region"]["경북"][0]["tel"], "053-111-2222")
        self.assertEqual(new["by_region"]["경북 봉화군"][0]["tel"], "")

    def test_guard_rejects_big_drop_in_phones(self):
        old = {"by_region": {"경북": [{"tel": "054-1"}] * 10}}
        worse = {"by_region": {"경북": [{"tel": "054-1"}] * 5 + [{"tel": ""}] * 5}}
        same = {"by_region": {"경북": [{"tel": "054-1"}] * 9 + [{"tel": ""}]}}
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "contacts.json")
            u.write_json(path, old)
            with self.assertRaises(RuntimeError):
                u.check_not_worse(path, worse)
            u.check_not_worse(path, same)
            u.check_not_worse(os.path.join(d, "none.json"), worse)


if __name__ == "__main__":
    unittest.main()
