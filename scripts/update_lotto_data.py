#!/usr/bin/env python3
"""동행복권에서 로또 6/45 역대 당첨번호를 받아 lotto_data.js 로 저장합니다.
사용법: python3 update_lotto_data.py [저장할 lotto_data.js 경로]
경로를 생략하면 이 스크립트와 같은 폴더에 저장합니다.
이미 받은 회차는 건너뛰고 새 회차만 추가로 받습니다."""
import json, os, re, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, "lotto_data.js")
URL = "https://www.dhlottery.co.kr/lt645/selectPstLt645Info.do?srchLtEpsd={}"


def load_existing():
    if not os.path.exists(OUT):
        return []
    m = re.search(r"=\s*(\[.*\]);", open(OUT, encoding="utf-8").read(), re.S)
    return json.loads(m.group(1)) if m else []


def fetch(rnd):
    req = urllib.request.Request(URL.format(rnd), headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.load(r)
    lst = (data.get("data") or {}).get("list") or []
    for d in lst:
        if d.get("ltEpsd") == rnd and d.get("tm1WnNo"):
            nums = sorted(d[f"tm{i}WnNo"] for i in range(1, 7))
            y = d["ltRflYmd"]
            return {"r": rnd, "d": f"{y[:4]}-{y[4:6]}-{y[6:]}", "n": nums, "b": d["bnsWnNo"]}
    return None


def write(rows):
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("// 동행복권 로또 6/45 역대 당첨번호 (update_lotto_data.py 로 생성)\n")
        f.write("window.LOTTO_DATA = " + json.dumps(rows, separators=(",", ":")) + ";\n")


def main():
    rows = load_existing()
    rnd = rows[-1]["r"] + 1 if rows else 1
    added = 0
    while True:
        row, err = None, None
        for attempt in range(5):  # 일시적인 연결 오류는 재시도
            try:
                row = fetch(rnd)
                err = None
                break
            except Exception as e:
                err = e
                time.sleep(2 * (attempt + 1))
        if err:
            print(f"{rnd}회 요청 실패: {err}")
            break
        if not row:
            break
        rows.append(row)
        added += 1
        if added % 50 == 0:
            write(rows)
            print(f"{rnd}회까지 받음", flush=True)
        rnd += 1
        time.sleep(0.1)
    write(rows)
    last = rows[-1] if rows else None
    print(f"새로 {added}회 추가, 총 {len(rows)}회" + (f" (최신 {last['r']}회 {last['d']})" if last else ""))
    if err:
        sys.exit(1)  # 사이트 접속 실패 → 자동 실행에서 실패로 표시되어 알림이 감


if __name__ == "__main__":
    main()
