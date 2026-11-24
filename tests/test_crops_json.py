import json
import os
import unittest

PATH = os.path.join(os.path.dirname(__file__), "..", "data", "crops", "crops.json")
KEYS = {"key", "name", "category", "desc", "main_regions", "aliases", "seed_type", "photo"}


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(PATH, encoding="utf-8") as f:
            cls.crops = json.load(f)

    def test_schema(self):
        for c in self.crops:
            self.assertTrue(KEYS <= c.keys(), c.get("name"))
            self.assertIn(c["category"], {"곡물", "채소", "과일", "특용작물"}, c["name"])
            self.assertIn(c["seed_type"], {"tree", "seed"}, c["name"])
            self.assertEqual(c["aliases"][0], c["name"])

    def test_unique_keys(self):
        self.assertEqual(len({c["key"] for c in self.crops}), len(self.crops))
        self.assertEqual(len({c["name"] for c in self.crops}), len(self.crops))

    def test_count(self):
        self.assertTrue(45 <= len(self.crops) <= 60, len(self.crops))

    def test_photo_source(self):
        root = os.path.join(os.path.dirname(__file__), "..")
        for c in self.crops:
            url = c["photo"]["url"]
            self.assertTrue(c["photo"]["license"], c["name"])
            self.assertTrue(c["photo"]["page"].startswith("https://commons.wikimedia.org/"), c["name"])
            if url.startswith("images/crops/"):
                # 위키미디어 사진을 잘라 저장한 경우: 파일이 있고 '일부 확대' 같은 설명이 있어야 함
                self.assertTrue(os.path.exists(os.path.join(root, url)), c["name"])
                self.assertTrue(c["photo"].get("note"), c["name"])
            else:
                self.assertRegex(url, r"^https://(upload|thumb)\.wikimedia\.org/[^?]+$", c["name"])

    def test_bokbunja_uses_fruit_crop(self):
        rubus = next(c for c in self.crops if c["key"] == "rubus")
        self.assertEqual(rubus["photo"]["url"], "images/crops/rubus.jpg")


if __name__ == "__main__":
    unittest.main()
