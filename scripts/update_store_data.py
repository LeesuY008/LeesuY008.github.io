#!/usr/bin/env python3
"""동행복권에서 로또 6/45 회차별 1등 당첨 판매점을 받아 stores_data.js 로 저장합니다.

사용법
  python3 update_store_data.py [stores_data.js] [lotto_data.js]
      새 회차만 받습니다. (매주 자동 업데이트용)
  python3 update_store_data.py [stores_data.js] [lotto_data.js] --backfill 60
      예전 회차를 최대 60회 다시 받아 주소·좌표를 보완합니다.
      사이트가 요청을 막으면 바로 멈추고, 다음 실행 때 이어서 받습니다.
  python3 update_store_data.py [stores_data.js] --normalize
      이미 받은 데이터의 지역 분류만 다시 계산합니다.

경로를 생략하면 이 스크립트와 같은 폴더의 파일을 씁니다.
판매점 정보는 262회부터 공개되어 있습니다."""
import json, os, re, sys, time, urllib.request
from datetime import date

args = [a for a in sys.argv[1:] if not a.startswith("--")]
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(args[0]) if len(args) > 0 else os.path.join(HERE, "stores_data.js")
LOTTO = os.path.abspath(args[1]) if len(args) > 1 else os.path.join(HERE, "lotto_data.js")
BACKFILL = int(sys.argv[sys.argv.index("--backfill") + 1]) if "--backfill" in sys.argv else 0
NORMALIZE = "--normalize" in sys.argv

URL = "https://www.dhlottery.co.kr/wnprchsplcsrch/selectLtWnShp.do?srchWnShpRnk=1&srchLtEpsd={}&srchShpLctn="
FIRST_ROUND = 262
TYPE = {"자동": 0, "수동": 1, "반자동": 2}
NEW_DELAY = 1.0        # 새 회차 받을 때 요청 간격(초)
BACKFILL_DELAY = 5.0   # 예전 회차 다시 받을 때 요청 간격(초) - 사이트 제한을 피하려고 느리게

# 17개 시·도 (저장은 짧은 이름, 화면에는 공식 이름으로 표시)
REGION_ALIASES = {
    "서울": ["서울", "서울시", "서울특별시"], "부산": ["부산", "부산시", "부산광역시"],
    "대구": ["대구", "대구시", "대구광역시"], "인천": ["인천", "인천시", "인천광역시"],
    "광주": ["광주", "광주시", "광주광역시"], "대전": ["대전", "대전시", "대전광역시"],
    "울산": ["울산", "울산시", "울산광역시"], "세종": ["세종", "세종시", "세종특별자치시"],
    "경기": ["경기", "경기도"], "강원": ["강원", "강원도", "강원특별자치도"],
    "충북": ["충북", "충청북도"], "충남": ["충남", "충청남도"],
    "전북": ["전북", "전라북도", "전북특별자치도"], "전남": ["전남", "전라남도"],
    "경북": ["경북", "경상북도"], "경남": ["경남", "경상남도"],
    "제주": ["제주", "제주도", "제주특별자치도"],
}
TOKEN_TO_REGION = {alias: key for key, names in REGION_ALIASES.items() for alias in names}
UNKNOWN = "지역 미상"


def region_of(addr, region_field=""):
    """주소 첫 단어(또는 동행복권 지역 값)로 17개 시·도 중 하나를 고릅니다."""
    toks = (addr or "").split(" ")
    for cand in (toks[0] if toks else "", (region_field or "").strip()):
        if cand == "전남광주":
            # 동행복권 데이터가 광주·전남을 '전남광주'로 묶어 줌 → 구(區)가 오면 광주광역시
            second = toks[1] if len(toks) > 1 else ""
            return "광주" if second.endswith("구") else "전남"
        if cand in TOKEN_TO_REGION:
            return TOKEN_TO_REGION[cand]
    return UNKNOWN


def read_js(path):
    m = re.search(r"=\s*(\{.*\}|\[.*\]);", open(path, encoding="utf-8").read(), re.S)
    return json.loads(m.group(1))


def load_existing():
    if os.path.exists(OUT):
        return read_js(OUT)
    return {"last": FIRST_ROUND - 1, "stores": {}, "wins": []}


def clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def has_region(addr):
    first = addr.split(" ")[0] if addr else ""
    return first in TOKEN_TO_REGION or first == "전남광주"


def store_info(s, old=None):
    name = clean(s.get("shpNm") or s.get("tradNm"))
    addr = clean(s.get("shpAddr"))
    # 폐점한 곳은 주소가 비거나 일부만 남아 있어서 다른 주소 필드로 보완
    for alt in (s.get("befAddr"), f"{s.get('rdnm') or ''} {s.get('daddr') or ''}"):
        alt = clean(alt)
        if alt and not has_region(addr) and has_region(alt):
            addr = alt
    if old and not has_region(addr) and has_region(old.get("a", "")):
        addr = old["a"]                      # 예전에 받은 주소가 더 온전하면 유지
    if "인터넷" in name or "dhlottery" in addr:
        region = "온라인"
    else:
        region = region_of(addr, s.get("region"))
    lat, lng = s.get("shpLat"), s.get("shpLot")
    if old and not lat:
        lat, lng = old.get("y"), old.get("x")
    return {"n": name, "a": addr, "g": region, "c": 1 if s.get("status") == "폐점" else 0, "y": lat, "x": lng}


def fetch(rnd, timeout=15):
    req = urllib.request.Request(URL.format(rnd), headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    return (data.get("data") or {}).get("list") or []


def write(db):
    db["updated"] = date.today().isoformat()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("// 동행복권 로또 6/45 회차별 1등 당첨 판매점 (update_store_data.py 로 생성)\n")
        f.write("window.STORE_DATA = " + json.dumps(db, ensure_ascii=False, separators=(",", ":")) + ";\n")


def normalize(db):
    for st in db["stores"].values():
        if st["g"] != "온라인":
            st["g"] = region_of(st.get("a", ""), st.get("g"))


def apply_round(db, rnd, lst):
    """한 회차의 1등 판매점을 반영합니다. (다시 받은 회차는 기존 기록을 교체)"""
    db["wins"] = [w for w in db["wins"] if w[0] != rnd]
    for s in lst:
        sid = str(s.get("ltShpId"))
        db["stores"][sid] = store_info(s, db["stores"].get(sid))
        db["wins"].append([rnd, sid, TYPE.get(s.get("atmtPsvYnTxt"), 0)])


def update_new(db):
    target = read_js(LOTTO)[-1]["r"]
    added, err = 0, None
    for rnd in range(db["last"] + 1, target + 1):
        for attempt in range(5):
            try:
                lst = fetch(rnd)
                err = None
                break
            except Exception as e:
                err = e
                time.sleep(10 * (attempt + 1))
        if err:
            print(f"{rnd}회 요청 실패: {err}")
            break
        apply_round(db, rnd, lst)
        db["last"] = rnd
        added += 1
        time.sleep(NEW_DELAY)
    db["wins"].sort(key=lambda w: (w[0], w[1]))
    print(f"새로 {added}회 추가, {db['last']}회까지 · 판매점 {len(db['stores'])}곳 · 1등 {len(db['wins'])}건")
    return err


def backfill(db, limit):
    """예전 회차를 천천히 다시 받아 주소·좌표를 보완합니다. 막히면 멈추고 다음에 이어서."""
    start = db.setdefault("bf", FIRST_ROUND)
    if start > db["last"]:
        print("보완할 회차가 없어요. (모두 다시 받음)")
        return
    done = 0
    for rnd in range(start, min(db["last"], start + limit - 1) + 1):
        try:
            lst = fetch(rnd, timeout=20)
        except Exception as e:
            print(f"{rnd}회에서 사이트가 응답하지 않아 멈춰요. 다음 실행 때 이어서 받아요. ({e})")
            break
        if lst:
            apply_round(db, rnd, lst)
        db["bf"] = rnd + 1
        done += 1
        if done % 20 == 0:
            write(db)
            print(f"{rnd}회까지 보완", flush=True)
        time.sleep(BACKFILL_DELAY)
    db["wins"].sort(key=lambda w: (w[0], w[1]))
    left = max(0, db["last"] - db.get("bf", FIRST_ROUND) + 1)
    print(f"보완 {done}회 · 다음 시작 {db.get('bf')}회 · 남은 회차 {left}회")


def main():
    db = load_existing()
    normalize(db)
    if NORMALIZE:
        write(db)
        print("지역 분류를 다시 계산했어요.")
        return
    if BACKFILL:
        backfill(db, BACKFILL)
        write(db)
        return
    err = update_new(db)
    write(db)
    if err:
        sys.exit(1)


if __name__ == "__main__":
    main()
