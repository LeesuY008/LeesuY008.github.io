"""농산물 판매처 찾기(crops.html) 데이터 변환 함수.

update_crop_data.py 가 공공데이터를 받아 이 함수들로 정리한다.
"""
import csv
import html
import io
import re

# 짧은 키 → 공식 이름 (화면 표시용)
SIDO_NAMES = {
    "서울": "서울특별시", "부산": "부산광역시", "대구": "대구광역시", "인천": "인천광역시",
    "광주": "광주광역시", "대전": "대전광역시", "울산": "울산광역시", "세종": "세종특별자치시",
    "경기": "경기도", "강원": "강원특별자치도", "충북": "충청북도", "충남": "충청남도",
    "전북": "전북특별자치도", "전남": "전라남도", "경북": "경상북도", "경남": "경상남도",
    "제주": "제주특별자치도",
}
_ALIASES = {
    "강원도": "강원", "전라북도": "전북", "제주도": "제주",
    "충청북도": "충북", "충청남도": "충남", "전라남도": "전남", "경상북도": "경북", "경상남도": "경남",
}
# 다른 시·도로 옮겨간 시·군 (2023-07 군위군 → 대구)
_MOVED = {"군위군": "대구"}
# 전남·광주 통합 명칭: 자치구(…구)는 광주, 시·군은 전남으로 나눈다
_MERGED_JG = ("전남광주통합특별시", "전남광주")

def normalize_sido(raw):
    s = (raw or "").strip()
    if s in SIDO_NAMES:
        return s
    if s in _ALIASES:
        return _ALIASES[s]
    for key, full in SIDO_NAMES.items():
        if s == full:
            return key
    return ""


def split_region(addr):
    parts = (addr or "").split()
    if not parts:
        return ("", "")
    sido = normalize_sido(parts[0])
    merged = parts[0] in _MERGED_JG
    sigungu = ""
    if (sido or merged) and sido != "세종" and len(parts) > 1 and re.search(r"[시군구]$", parts[1]):
        sigungu = parts[1]
    if merged:
        sido = "광주" if sigungu.endswith("구") else "전남"
    if sigungu in _MOVED:
        sido = _MOVED[sigungu]
    return (sido, sigungu)


def match_crop(item_raw, crops):
    """품목 이름 → 작물 키.

    1) 괄호 앞 이름이나 괄호 안 이름이 별칭과 정확히 같으면 그 작물
    2) 아니면 두 글자 이상 별칭 중 가장 긴 것이 포함된 작물 ("청양고추" → 고추)
    한 글자 별칭("배", "무")은 정확히 같을 때만 쓴다. "배추", "무화과" 오인 방지.
    작물의 exclude 단어가 들어 있으면 그 작물은 후보에서 뺀다 ("산딸기"는 딸기가 아님).
    """
    text = re.sub(r"\s+", "", item_raw or "")
    words = [w for w in re.split(r"[()\[\],/·]", text) if w]
    cands = [c for c in crops if not any(x in text for x in c.get("exclude", []))]
    for crop in cands:
        if any(a in words for a in crop["aliases"]):
            return crop["key"]
    best, best_len = None, 0
    for crop in cands:
        for a in crop["aliases"]:
            if len(a) >= 2 and a in text and len(a) > best_len:
                best, best_len = crop["key"], len(a)
    return best


def _num(v):
    try:
        return float(str(v).replace(",", "")) if str(v).strip() else 0.0
    except ValueError:
        return 0.0


def summarize_gap(rows, crops):
    """GAP 인증농가 현황(필지 단위) → {작물키: [{sido, sigungu, certs, area_m2, plan_t}]} (면적 큰 순)

    원본에는 농가 이름이 없다. 인증번호 수를 '인증 건수'로 센다.
    """
    acc, item_cache = {}, {}
    for r in rows:
        item = r.get("품목", "")
        if item not in item_cache:
            item_cache[item] = match_crop(item, crops)
        key = item_cache[item]
        if not key:
            continue
        sido, sigungu = split_region(r.get("소재지"))
        if not sido:
            continue
        a = acc.setdefault((key, sido, sigungu), {"certs": set(), "area": 0.0, "plan": 0.0})
        a["certs"].add(r.get("인증번호"))
        a["area"] += _num(r.get("재배면적(㎡)"))
        a["plan"] += _num(r.get("생산계획량(톤)"))
    out = {}
    for (key, sido, sigungu), a in acc.items():
        out.setdefault(key, []).append({"sido": sido, "sigungu": sigungu, "certs": len(a["certs"]),
                                        "area_m2": round(a["area"]), "plan_t": round(a["plan"], 1)})
    for v in out.values():
        v.sort(key=lambda x: -x["area_m2"])
    return out


def contacts_for(sido, sigungu, contacts):
    if sigungu and contacts.get(f"{sido} {sigungu}"):
        return contacts[f"{sido} {sigungu}"]
    return contacts.get(sido, [])



def load_csv_rows(raw):
    """공공데이터 CSV(UTF-8 또는 CP949) → dict 목록"""
    for enc in ("utf-8-sig", "cp949"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("알 수 없는 인코딩")
    return [{(k or "").strip(): (v or "").strip() for k, v in r.items()} for r in csv.DictReader(io.StringIO(text))]


def normalize_phone(raw):
    d = re.sub(r"\D", "", raw or "")
    if re.fullmatch(r"1[5-9]\d{6}", d):
        return f"{d[:4]}-{d[4:]}"
    if d.startswith("02") and len(d) in (9, 10):
        return f"02-{d[2:-4]}-{d[-4:]}"
    if re.fullmatch(r"0\d{2}\d{7,8}", d):
        return f"{d[:3]}-{d[3:-4]}-{d[-4:]}"
    return ""


_PHONE = r"0\d{1,2}\s*[)\-.]\s*\d{3,4}\s*[\-.]\s*\d{4}"


def extract_phone(page):
    """기관 홈페이지 HTML에서 대표 전화번호 하나. 팩스 번호는 건너뛴다."""
    text = html.unescape(re.sub(r"<[^>]+>", " ", page or ""))
    m = re.search(r"(대표\s*전화|대표\s*번호|전화|TEL|Tel|tel|문의)\s*[:.]?\s*(" + _PHONE + ")", text)
    if m:
        return normalize_phone(m.group(2))
    for m in re.finditer(_PHONE, text):
        if not re.search(r"(팩스|FAX|Fax|fax)", text[max(0, m.start() - 12):m.start()]):
            return normalize_phone(m.group(0))
    return ""


_JEJU_CITY = {"제주": "제주시", "서귀포": "서귀포시"}


def parse_rda_centers(page):
    """농촌진흥청 '지방농촌진흥기관' 페이지 → [{sido, sigungu, name, homepage}]"""
    out, seen, head = [], set(), ""
    for m in re.finditer(r'<h2 class="(sec-tit|pop-sub-tit)">([^<]*)</h2>|<a[^>]*href="(https?://[^"]+)"[^>]*>([^<]*)</a>', page):
        if m.group(1):
            if m.group(1) != "sec-tit":
                break
            head = m.group(2).split()[0]
            continue
        name = re.sub(r"농업\s+기술", "농업기술", html.unescape(m.group(4)).strip())
        if not re.search(r"농업기술(원|센터)$", name):
            continue
        pm = re.match(r"\((\S+)\)\s*(.*)", name)
        prefix, name = (pm.group(1), pm.group(2)) if pm else ("", name)
        token = name.split()[0]
        sido, sigungu = normalize_sido(token), ""
        if not sido:
            if token in _JEJU_CITY:
                sigungu = _JEJU_CITY[token]
            elif re.search(r"[시군구]$", token):
                sigungu = token
            base = prefix or head
            if base in _MERGED_JG:
                sido = "광주" if sigungu.endswith("구") else "전남"
            else:
                sido = normalize_sido(base)
            if sigungu in _MOVED:
                sido = _MOVED[sigungu]
        key = (name, m.group(3))
        if sido and key not in seen:
            seen.add(key)
            out.append({"sido": sido, "sigungu": sigungu, "name": name, "homepage": m.group(3)})
    return out


def _store_key(name):
    return re.sub(r"^\([^)]*\)|\s+", "", name or "")


def merge_stores(mafra_rows, at_rows):
    """농림부 직매장 목록(전화 없음) + aT 판매장 목록(전화 있음) → 직매장 목록"""
    out = {}
    for r in at_rows:
        name = re.sub(r"^\([^)]*\)\s*", "", r.get("마켓 명", "")).strip()
        sido, sigungu = split_region(r.get("주소"))
        out[_store_key(name)] = {"type": "직매장", "name": name, "addr": r.get("주소", ""),
                                 "tel": normalize_phone(r.get("전화번호")), "hours": r.get("기간", ""),
                                 "sido": sido, "sigungu": sigungu}
    for r in mafra_rows:
        key = _store_key(r.get("매장명"))
        if key in out:
            continue
        sido, sigungu = split_region(r.get("주소"))
        out[key] = {"type": "직매장", "name": r.get("매장명", "").strip(), "addr": r.get("주소", ""),
                    "tel": "", "hours": "", "sido": sido, "sigungu": sigungu}
    return [v for v in out.values() if v["sido"]]
