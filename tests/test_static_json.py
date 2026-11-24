import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from crop_lib import SIDO_NAMES  # noqa: E402

D = os.path.join(os.path.dirname(__file__), "..", "data", "crops")
TEL = re.compile(r"^(0\d{1,2}-\d{3,4}-\d{4}|1\d{3}-\d{4})?$")


def load(name):
    with open(os.path.join(D, name), encoding="utf-8") as f:
        return json.load(f)


class T(unittest.TestCase):
    def check_regions(self, by_region):
        for key, rows in by_region.items():
            self.assertIn(key.split()[0], SIDO_NAMES, key)
            for r in rows:
                self.assertRegex(r["tel"], TEL, r["name"])

    def test_contacts_json_shape(self):
        c = load("contacts.json")
        self.assertTrue(c["meta"]["sources"])
        self.check_regions(c["by_region"])
        self.assertGreaterEqual(sum(len(v) for v in c["by_region"].values()), 150)

    def test_stores_json_shape(self):
        s = load("stores.json")
        self.check_regions(s["by_region"])
        self.assertGreaterEqual(sum(len(v) for v in s["by_region"].values()), 100)

    def test_nurseries_json_shape(self):
        n = load("nurseries.json")
        for it in n["items"]:
            self.assertTrue(it["name"])
            self.assertNotRegex(it["name"], r"_\d+호$")


if __name__ == "__main__":
    unittest.main()
