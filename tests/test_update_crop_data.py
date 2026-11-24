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


if __name__ == "__main__":
    unittest.main()
