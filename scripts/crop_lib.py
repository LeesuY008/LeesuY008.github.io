"""농산물 판매처 찾기(crops.html) 데이터 변환 함수.

update_crop_data.py 가 공공데이터를 받아 이 함수들로 정리한다.
"""
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

# 공공데이터 원본 항목 이름 → 내부 이름. 실제 응답에 맞춰 바꾼다.
FIELD_MAP = {
    "group": "생산단체명", "person": "생산자명", "addr": "소재지",
    "item": "품목", "area": "재배면적", "cert": "인증번호",
}


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
    sigungu = ""
    if sido and sido != "세종" and len(parts) > 1 and re.search(r"[시군구]$", parts[1]):
        sigungu = parts[1]
    if sigungu in _MOVED:
        sido = _MOVED[sigungu]
    return (sido, sigungu)


def mask_name(name):
    s = re.sub(r"\s+", "", name or "")
    if len(s) <= 1:
        return s
    return s[0] + "○" * (len(s) - 1)


def match_crop(item_raw, crops):
    """품목 이름 → 작물 키.

    1) 괄호 앞 이름이나 괄호 안 이름이 별칭과 정확히 같으면 그 작물
    2) 아니면 두 글자 이상 별칭 중 가장 긴 것이 포함된 작물 ("청양고추" → 고추)
    한 글자 별칭("배", "무")은 정확히 같을 때만 쓴다. "배추", "무화과" 오인 방지.
    """
    text = re.sub(r"\s+", "", item_raw or "")
    words = [w for w in re.split(r"[()\[\],/·]", text) if w]
    for crop in crops:
        if any(a in words for a in crop["aliases"]):
            return crop["key"]
    best, best_len = None, 0
    for crop in crops:
        for a in crop["aliases"]:
            if len(a) >= 2 and a in text and len(a) > best_len:
                best, best_len = crop["key"], len(a)
    return best


def _num(v):
    try:
        return float(str(v).replace(",", "")) if str(v).strip() else None
    except ValueError:
        return None


def farm_record(row, crop_key):
    f = FIELD_MAP
    group = (row.get(f["group"]) or "").strip()
    sido, sigungu = split_region(row.get(f["addr"]))
    return {
        "name": group or mask_name(row.get(f["person"])),
        "kind": "group" if group else "person",
        "crop": crop_key,
        "item": (row.get(f["item"]) or "").strip(),
        "sido": sido, "sigungu": sigungu,
        "area_m2": _num(row.get(f["area"])),
        "cert_no": (row.get(f["cert"]) or "").strip(),
    }


def contacts_for(sido, sigungu, contacts):
    if sigungu and contacts.get(f"{sido} {sigungu}"):
        return contacts[f"{sido} {sigungu}"]
    return contacts.get(sido, [])

