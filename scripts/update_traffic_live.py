"""서울시 실시간 교통 정보 수집 → data/traffic_live.json

GitHub Actions(update-traffic.yml)에서 약 10분마다 실행된다.
- 실시간 도로 소통 정보(TrafficInfo): 링크별 속도(km/h)
- 교통량 이력 정보(VolInfo): 교통량 조사지점 139곳의 최근 1시간 교통량

인증키는 저장소 Secret `SEOUL_API_KEY` 로만 받는다(코드·HTML에 넣지 않음).
사용법: python3 scripts/update_traffic_live.py data/seoul_links.json data/traffic_live.json
"""
import json
import os
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
BASE = "http://openapi.seoul.go.kr:8088/{key}/xml/{svc}/1/{end}/{args}"  # 교통량 이력은 XML만 제공
SPOTS = [  # 서울시 교통량 조사지점 139곳 (TOPIS 2026년 10월 자료 기준)
    *[f"A-{i:02d}" for i in range(1, 25)], *[f"B-{i:02d}" for i in range(1, 39)],
    *[f"C-{i:02d}" for i in range(1, 22)], *[f"D-{i:02d}" for i in range(1, 47)],
    *[f"F-{i:02d}" for i in range(1, 11)],
]


def call(key, svc, args, end=1, tries=3):
    """서울시 OpenAPI(XML) 호출 → {"RESULT": {...}, "row": [dict, ...]}"""
    url = BASE.format(key=key, svc=svc, end=end, args=args)
    last = None
    for n in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                root = ET.fromstring(r.read())
            res = root if root.tag == "RESULT" else root.find("RESULT")
            result = {c.tag.upper(): (c.text or "") for c in res} if res is not None else {"CODE": "UNKNOWN"}
            # 태그 대소문자가 섞여 있어도 읽히도록 대문자로 통일
            rows = [{c.tag.upper(): (c.text or "") for c in row} for row in root.findall("row")]
            return {"RESULT": result, "row": rows}
        except Exception as e:  # 네트워크 오류는 잠깐 쉬고 재시도
            last = str(e)
            time.sleep(1.5 * (n + 1))
    return {"RESULT": {"CODE": "NETWORK", "MESSAGE": last}, "row": []}


def code_of(res):
    return (res.get("RESULT") or {}).get("CODE", "")


def main(links_path, out_path):
    key = os.environ.get("SEOUL_API_KEY", "").strip()
    if not key:
        # 키 등록 전에는 실패 알림이 반복되지 않도록 경고만 남기고 건너뜀
        print("::warning::SEOUL_API_KEY 가 없어 건너뜁니다. Settings → Secrets and variables → Actions 에 등록하세요.")
        return

    ids = json.load(open(links_path, encoding="utf-8"))["ids"]
    now = datetime.now(KST)

    # 1) 키·접속 확인 (실패하면 전체 수집을 하지 않음)
    probe = call(key, "TrafficInfo", ids[0])
    if code_of(probe) not in ("INFO-000", "INFO-200"):
        sys.exit(f"서울시 API 호출 실패: {probe.get('RESULT')}")

    # 2) 링크별 속도
    def speed(lid):
        res = call(key, "TrafficInfo", lid)
        rows = res.get("row") or []
        if rows:
            try:
                return round(float(rows[0]["PRCS_SPD"]))
            except (KeyError, TypeError, ValueError):
                return None
        return None

    with ThreadPoolExecutor(max_workers=16) as ex:
        spd = list(ex.map(speed, ids))

    # 3) 교통량: 현재 시각 기준 최근 시간부터 거슬러 올라가며 자료가 있는 시간 사용
    def volume(spot):
        for back in range(0, 4):
            t = now - timedelta(hours=back)
            res = call(key, "VolInfo", f"{spot}/{t:%Y%m%d}/{t:%H}/", end=200)
            rows = res.get("row") or []
            if rows:
                by_io = {}
                for r in rows:
                    io = str(r.get("IO_TYPE", "?"))
                    try:
                        by_io[io] = by_io.get(io, 0) + int(float(r.get("VOL") or 0))
                    except ValueError:
                        pass
                return {"ymd": f"{t:%Y%m%d}", "hh": int(t.strftime("%H")), "io": by_io}
        return None

    with ThreadPoolExecutor(max_workers=8) as ex:
        vols = dict(zip(SPOTS, ex.map(volume, SPOTS)))

    out = {
        "updated": now.isoformat(timespec="seconds"),
        "speed": spd,  # seoul_links.json 의 ids 순서와 같음 (km/h, 없으면 null)
        "speed_ok": sum(v is not None for v in spd),
        "vol": {k: v for k, v in vols.items() if v},
        "vol_ok": sum(1 for v in vols.values() if v),
    }
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"속도 {out['speed_ok']}/{len(ids)} 링크, 교통량 {out['vol_ok']}/{len(SPOTS)} 지점, 기준 {out['updated']}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
