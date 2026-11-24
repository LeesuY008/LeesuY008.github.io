import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from crop_lib import (contacts_for, farm_record, mask_name, match_crop,  # noqa: E402
                      normalize_sido, split_region)


class T(unittest.TestCase):
    def test_normalize_sido_variants(self):
        for raw, want in [("경상북도", "경북"), ("경북", "경북"), ("강원도", "강원"), ("강원특별자치도", "강원"),
                          ("전라북도", "전북"), ("전북특별자치도", "전북"), ("세종특별자치시", "세종"),
                          ("서울", "서울"), ("화성", "")]:
            self.assertEqual(normalize_sido(raw), want, raw)

    def test_normalize_gunwi(self):
        self.assertEqual(split_region("경상북도 군위군 군위읍"), ("대구", "군위군"))

    def test_split_region(self):
        self.assertEqual(split_region("경상북도 청송군 진보면 1"), ("경북", "청송군"))
        self.assertEqual(split_region("세종특별자치시 연서면"), ("세종", ""))

    def test_mask_name_edge_cases(self):
        self.assertEqual(mask_name("김철수"), "김○○")
        self.assertEqual(mask_name("이"), "이")
        self.assertEqual(mask_name(""), "")
        self.assertEqual(mask_name(" 박 영희 "), "박○○")

    def test_match_crop_alias(self):
        crops = [{"key": "apple", "aliases": ["사과", "후지"]}]
        self.assertEqual(match_crop("사과(후지)", crops), "apple")
        self.assertIsNone(match_crop("배추", crops))

    def test_farm_record_group_vs_person(self):
        g = farm_record({"생산단체명": "청송사과영농조합", "생산자명": "", "소재지": "경상북도 청송군", "품목": "사과",
                         "재배면적": "1200", "인증번호": "G1"}, "apple")
        self.assertEqual((g["name"], g["kind"], g["sido"], g["sigungu"]), ("청송사과영농조합", "group", "경북", "청송군"))
        p = farm_record({"생산단체명": "", "생산자명": "김철수", "소재지": "경상북도 청송군", "품목": "사과",
                         "재배면적": "", "인증번호": "G2"}, "apple")
        self.assertEqual((p["name"], p["kind"], p["area_m2"]), ("김○○", "person", None))

    def test_contacts_fallback_to_sido(self):
        c = {"경북 청송군": [{"name": "청송군농업기술센터"}], "경북": [{"name": "경북농업기술원"}]}
        self.assertEqual(contacts_for("경북", "청송군", c)[0]["name"], "청송군농업기술센터")
        self.assertEqual(contacts_for("경북", "영양군", c)[0]["name"], "경북농업기술원")
        self.assertEqual(contacts_for("제주", "", c), [])


if __name__ == "__main__":
    unittest.main()
