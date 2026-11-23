#!/usr/bin/env python3
"""동행복권에서 로또 6/45 회차별 1등 당첨 판매점을 받아 stores_data.js 로 저장합니다.
사용법: python3 update_store_data.py [stores_data.js 경로] [lotto_data.js 경로]
경로를 생략하면 이 스크립트와 같은 폴더의 파일을 씁니다.
이미 받은 회차는 건너뛰고, lotto_data.js 의 최신 회차까지만 새로 받습니다.
(판매점 정보는 262회부터 공개되어 있습니다.)"""
import json, os, re, sys, time, urllib.request
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, "stores_data.js")
LOTTO = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.join(HERE, "lotto_data.js")
URL = "https://www.dhlottery.co.kr/wnprchsplcsrch/selectLtWnShp.do?srchWnShpRnk=1&srchLtEpsd={}&srchShpLctn="
FIRST_ROUND = 262
TYPE = {"자동": 0, "수동": 1, "반자동": 2}
REGIONS = {"서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남",
           "전북", "전남", "경북", "경남", "제주", "전남광주"}


def read_js(path):
    m = re.search(r"=\s*(\{.*\}|\[.*\]);", open(path, encoding="utf-8").read(), re.S)
    return json.loads(m.group(1))


def load_existing():
    if os.path.exists(OUT):
        return read_js(OUT)
    return {"last": FIRST_ROUND - 1, "stores": {}, "wins": []}


def latest_round():
    rows = read_js(LOTTO)
    return rows[-1]["r"]


def clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def store_info(s):
    name = clean(s.get("shpNm") or s.get("tradNm"))
    addr = clean(s.get("shpAddr"))
    # 폐점한 곳은 주소가 비거나 일부만 남아 있어서 다른 주소 필드로 보완
    for alt in (s.get("befAddr"), f"{s.get('rdnm') or ''} {s.get('daddr') or ''}"):
        alt = clean(alt)
        if alt and (not addr or addr.split(" ")[0] not in REGIONS) and alt.split(" ")[0] in REGIONS:
            addr = alt
    region = clean(s.get("region"))
    if "인터넷" in name or "dhlottery" in addr:
        region = "온라인"
    elif region not in REGIONS:
        first = addr.split(" ")[0] if addr else ""
        region = first if first in REGIONS else "기타"
    return {
        "n": name, "a": addr, "g": region,
        "c": 1 if s.get("status") == "폐점" else 0,
        "y": s.get("shpLat"), "x": s.get("shpLot"),
    }


def fetch(rnd):
    req = urllib.request.Request(URL.format(rnd), headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.load(r)
    return (data.get("data") or {}).get("list") or []


def write(db):
    db["updated"] = date.today().isoformat()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("// 동행복권 로또 6/45 회차별 1등 당첨 판매점 (update_store_data.py 로 생성)\n")
        f.write("window.STORE_DATA = " + json.dumps(db, ensure_ascii=False, separators=(",", ":")) + ";\n")


def main():
    db = load_existing()
    target = latest_round()
    err = None
    added = 0
    for rnd in range(db["last"] + 1, target + 1):
        for attempt in range(5):
            try:
                lst = fetch(rnd)
                err = None
                break
            except Exception as e:
                err = e
                time.sleep(2 * (attempt + 1))
        if err:
            print(f"{rnd}회 요청 실패: {err}")
            break
        for s in lst:
            sid = str(s.get("ltShpId"))
            db["stores"][sid] = store_info(s)
            db["wins"].append([rnd, sid, TYPE.get(s.get("atmtPsvYnTxt"), 0)])
        db["last"] = rnd
        added += 1
        if added % 100 == 0:
            write(db)
            print(f"{rnd}회까지 받음", flush=True)
        time.sleep(0.08)
    write(db)
    print(f"새로 {added}회 추가, {db['last']}회까지 · 판매점 {len(db['stores'])}곳 · 1등 {len(db['wins'])}건")
    if err:
        sys.exit(1)


if __name__ == "__main__":
    main()
