"""농산물 판매처 찾기(crops.html) 데이터 갱신 → data/crops/

  python3 scripts/update_crop_data.py data/crops            GAP 인증 농가 갱신 (Secret DATA_GO_KR_KEY 필요)
  python3 scripts/update_crop_data.py data/crops --static   문의처·직매장·씨앗·묘목 업체 갱신 (키 필요 없음)

실패하면 기존 파일을 그대로 두고 0이 아닌 코드로 끝낸다.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
from crop_lib import extract_phone, load_csv_rows, merge_stores, parse_rda_centers, split_region  # noqa: E402
from sources import SOURCES  # noqa: E402

KST = timezone(timedelta(hours=9))
UA = {"User-Agent": "Mozilla/5.0 (crop-finder data update)"}


def http(url, data=None, timeout=30, tries=3):
    last = None
    for n in range(tries):
        try:
            body = urllib.parse.urlencode(data).encode() if data else None
            with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - 네트워크 오류는 재시도 후 그대로 올린다
            last = e
            time.sleep(2 * (n + 1))
    raise last


def data_go_file(pk):
    """공공데이터포털 파일데이터 최신본 → (bytes, 데이터 이름)"""
    import re
    page = http(f"https://www.data.go.kr/data/{pk}/fileData.do").decode("utf-8", "replace")
    m = re.search(r"fn_fileDataDown\('%s', '(uddi:[^']+)'" % pk, page)
    if not m:
        raise RuntimeError(f"{pk}: 다운로드 정보를 찾지 못함")
    info = json.loads(http("https://www.data.go.kr/tcs/dss/selectFileDataDownload.do", {
        "publicDataPk": pk, "publicDataDetailPk": m.group(1), "fileDetailSn": 1, "publicDataTyCode": "PR0051"}))
    raw = http("https://www.data.go.kr/cmm/cmm/fileDownload.do?" + urllib.parse.urlencode(
        {"atchFileId": info["atchFileId"], "fileDetailSn": info["fileDetailSn"]}))
    return raw, info["dataSetFileDetailInfo"]["dataNm"]


def write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)


def meta(*names):
    return {"sources": list(names), "updated": datetime.now(KST).strftime("%Y-%m-%d")}


def build_contacts():
    src = SOURCES["centers"]
    centers = parse_rda_centers(http(src["url"]).decode("utf-8", "replace"))
    if len(centers) < 150:
        raise RuntimeError(f"농업기술센터 목록이 너무 적음: {len(centers)}")

    def phone(c):
        try:
            return extract_phone(http(c["homepage"], timeout=15, tries=2).decode("utf-8", "replace"))
        except Exception:  # noqa: BLE001 - 홈페이지가 안 열리면 전화번호 없이 링크만
            return ""

    with ThreadPoolExecutor(8) as ex:
        phones = list(ex.map(phone, centers))
    by_region = {}
    for c, tel in zip(centers, phones):
        key = f"{c['sido']} {c['sigungu']}".strip()
        by_region.setdefault(key, []).append({"type": "농업기술센터" if c["name"].endswith("센터") else "농업기술원",
                                             "name": c["name"], "tel": tel, "homepage": c["homepage"]})
    return {"meta": meta(src["name"] + " (전화번호: 각 기관 홈페이지)"), "by_region": by_region}


def build_stores():
    mafra_raw, mafra_nm = data_go_file(SOURCES["stores_mafra"]["pk"])
    at_raw, at_nm = data_go_file(SOURCES["stores_at"]["pk"])
    stores = merge_stores(load_csv_rows(mafra_raw), load_csv_rows(at_raw))
    if len(stores) < 100:
        raise RuntimeError(f"직매장 목록이 너무 적음: {len(stores)}")
    by_region = {}
    for s in stores:
        by_region.setdefault(f"{s['sido']} {s['sigungu']}".strip(), []).append(
            {k: s[k] for k in ("name", "addr", "tel", "hours")})
    return {"meta": meta(mafra_nm, at_nm), "by_region": by_region}


def build_nurseries():
    raw, nm = data_go_file(SOURCES["nurseries"]["pk"])
    items = []
    for r in load_csv_rows(raw):
        get = lambda pre: next((v for k, v in r.items() if k.startswith(pre)), "")  # noqa: E731
        if get("노출여부") != "Y" or get("삭제여부") == "Y" or not get("회사명"):
            continue
        sido, sigungu = split_region(get("회사주소"))
        items.append({"name": get("회사명"), "addr": get("회사주소"), "sido": sido, "sigungu": sigungu,
                      "homepage": get("홈페이지 링크"), "products": get("대표 상품")})
    return {"meta": meta(nm), "items": items}


def run_static(out_dir):
    results = {"contacts.json": build_contacts(), "stores.json": build_stores(), "nurseries.json": build_nurseries()}
    for name, obj in results.items():  # 전부 성공한 뒤에만 쓴다
        write_json(os.path.join(out_dir, name), obj)
        print(name, "저장")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    out_dir = argv[1]
    os.makedirs(out_dir, exist_ok=True)
    try:
        if "--static" in argv:
            run_static(out_dir)
            return 0
        return run_gap(out_dir)
    except Exception as e:  # noqa: BLE001
        print("갱신 실패, 기존 파일 유지:", e, file=sys.stderr)
        return 1


def run_gap(out_dir):
    raise NotImplementedError("Task 4")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
