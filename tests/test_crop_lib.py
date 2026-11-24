import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from crop_lib import (contacts_for, extract_phone, farm_record, load_csv_rows,  # noqa: E402
                      mask_name, match_crop, merge_stores, normalize_phone, normalize_sido,
                      parse_rda_centers, split_region)

RDA_HTML = '''
<h2 class="sec-tit">농업기술원</h2>
<a href="https://nongup.gg.go.kr/" target="_blank">경기도 농업기술원</a>
<h2 class="sec-tit">특·광역시 및 관할시군 농업기술센터</h2>
<a href="https://a.example/" target="_blank">대구광역시 농업기술센터</a>
<a href="https://b.example/" target="_blank">(대구) 군위군 농업기술센터</a>
<h2 class="sec-tit">경기도 농업기술센터</h2>
<a href="https://c.example/" target="_blank">광주시 농업기술센터</a>
<h2 class="sec-tit">전남광주통합특별시 농업기술센터</h2>
<a href="https://d.example/" target="_blank">나주시 농업기술센터</a>
<h2 class="sec-tit">제주도 농업기술센터</h2>
<a href="https://e.example/" target="_blank">서귀포 농업기술센터</a>
<a href="https://f.example/" target="_blank">동부 농업기술센터</a>
<h2 class="pop-sub-tit">경기도 농업기술센터</h2>
'''


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

    def test_match_crop_prefers_exact_over_substring(self):
        crops = [{"key": "pear", "aliases": ["배"]}, {"key": "napa", "aliases": ["배추"]},
                 {"key": "pepper", "aliases": ["고추"]}, {"key": "radish", "aliases": ["무"]}]
        self.assertEqual(match_crop("배추", crops), "napa")
        self.assertEqual(match_crop("배(신고)", crops), "pear")
        self.assertEqual(match_crop("청양고추", crops), "pepper")
        self.assertIsNone(match_crop("무화과", crops))

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

    def test_split_region_merged_jeonnam_gwangju(self):
        self.assertEqual(split_region("전남광주통합특별시 나주시 빛가람로 1"), ("전남", "나주시"))
        self.assertEqual(split_region("전남광주통합특별시 북구 용봉로 77"), ("광주", "북구"))

    def test_load_csv_cp949(self):
        raw = "업체명,연락처\n우리농원,031-111-2222\n".encode("cp949")
        self.assertEqual(load_csv_rows(raw), [{"업체명": "우리농원", "연락처": "031-111-2222"}])
        self.assertEqual(load_csv_rows("\ufeffa\n1\n".encode("utf-8"))[0], {"a": "1"})

    def test_normalize_phone(self):
        self.assertEqual(normalize_phone("02.2058.0381"), "02-2058-0381")
        self.assertEqual(normalize_phone("054)880-2114"), "054-880-2114")
        self.assertEqual(normalize_phone("0548802114"), "054-880-2114")
        self.assertEqual(normalize_phone("1588-1234"), "1588-1234")
        self.assertEqual(normalize_phone("없음"), "")

    def test_parse_rda_centers(self):
        got = {(c["sido"], c["sigungu"], c["name"]) for c in parse_rda_centers(RDA_HTML)}
        self.assertEqual(got, {("경기", "", "경기도 농업기술원"), ("대구", "", "대구광역시 농업기술센터"),
                               ("대구", "군위군", "군위군 농업기술센터"), ("경기", "광주시", "광주시 농업기술센터"),
                               ("전남", "나주시", "나주시 농업기술센터"), ("제주", "서귀포시", "서귀포 농업기술센터"),
                               ("제주", "", "동부 농업기술센터")})

    def test_extract_phone_prefers_labelled(self):
        page = "<p>팩스 061-111-0000</p><p>대표전화 : 061) 339-7500</p><p>061-222-3333</p>"
        self.assertEqual(extract_phone(page), "061-339-7500")
        self.assertEqual(extract_phone("<p>문의 043-220-8000</p>"), "043-220-8000")
        self.assertEqual(extract_phone("<p>전화번호 없음</p>"), "")

    def test_merge_stores(self):
        mafra = [{"매장명": "원당농협로컬푸드직매장원당역점", "주소": "경기 고양시 덕양구 고양대로 1433"}]
        at = [{"마켓 명": "(경기)원당농협 로컬푸드직매장 원당역점", "주소": "경기도 고양시 덕양구 고양대로 1433",
               "기간": "09:00~20:00", "전화번호": "031.123.4567"},
              {"마켓 명": "(서울)영동농협 하나로마트 내곡점", "주소": "서울특별시 서초구 내곡동 341-10",
               "기간": "", "전화번호": "02.2058.0381"}]
        got = sorted(merge_stores(mafra, at), key=lambda r: r["name"])
        self.assertEqual(len(got), 2)
        won = [r for r in got if "원당" in r["name"]][0]
        self.assertEqual((won["tel"], won["sido"], won["sigungu"]), ("031-123-4567", "경기", "고양시"))


if __name__ == "__main__":
    unittest.main()
