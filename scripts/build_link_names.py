"""서울시 서비스링크별 도로명·구간 이름 목록 만들기 → data/seoul_link_names.json

도로명 검색 기능에 쓴다. 서울시 OpenAPI '소통 돌발 링크 정보(LinkInfo)'를
링크마다 한 번씩 불러 도로명(ROAD_NAME), 시작/종료 지점명, 길이(MAP_DIST)를 모은다.
도로 정보는 자주 바뀌지 않으므로 GitHub Actions에서 파일이 없거나 30일이 지났을 때만 실행한다.

사용법: python3 scripts/build_link_names.py data/seoul_links.json data/seoul_link_names.json
"""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
from update_traffic_live import call  # 같은 XML 호출 함수 재사용

KST = timezone(timedelta(hours=9))


def main(links_path, out_path):
    key = os.environ.get("SEOUL_API_KEY", "").strip()
    if not key:
        print("::warning::SEOUL_API_KEY 가 없어 도로명 목록 생성을 건너뜁니다.")
        return
    if os.path.exists(out_path):  # 30일 안에 만든 목록이 있으면 건너뜀
        try:
            made = datetime.fromisoformat(json.load(open(out_path, encoding="utf-8"))["updated"])
            if datetime.now(KST) - made < timedelta(days=30):
                print(f"도로명 목록이 최신입니다({made:%Y-%m-%d}). 건너뜀")
                return
        except Exception:
            pass
    ids = json.load(open(links_path, encoding="utf-8"))["ids"]

    def info(lid):
        res = call(key, "LinkInfo", f"{lid}/")
        rows = res.get("row") or []
        if not rows:
            return None
        r = rows[0]
        try:
            dist = round(float(r.get("MAP_DIST") or 0))
        except ValueError:
            dist = 0
        return [r.get("ROAD_NAME", "").strip(), r.get("ST_NODE_NM", "").strip(),
                r.get("ED_NODE_NM", "").strip(), dist]

    with ThreadPoolExecutor(max_workers=16) as ex:
        rows = list(ex.map(info, ids))

    ok = sum(r is not None for r in rows)
    if ok < len(ids) * 0.5:   # 절반도 못 받았으면 저장하지 않음
        sys.exit(f"도로명 정보를 충분히 받지 못했습니다: {ok}/{len(ids)}")
    out = {
        "updated": datetime.now(KST).isoformat(timespec="seconds"),
        "src": "서울시 소통 돌발 링크 정보(LinkInfo) OpenAPI",
        # seoul_links.json 의 ids 순서와 같음: [도로명, 시작 지점명, 종료 지점명, 길이(m)] 또는 null
        "rows": rows,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"도로명 정보 {ok}/{len(ids)} 링크 저장")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
