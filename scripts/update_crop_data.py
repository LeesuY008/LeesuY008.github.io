"""농산물 판매처 찾기(crops.html) 데이터 갱신 → data/crops/

  python3 scripts/update_crop_data.py data/crops            GAP 인증 현황 갱신 (농림축산식품 공공데이터 포털 CSV)
  python3 scripts/update_crop_data.py data/crops --static   문의처·직매장·씨앗·묘목 업체 갱신 (키 필요 없음)

실패하면 기존 파일을 그대로 두고 0이 아닌 코드로 끝낸다.
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
from crop_lib import (extract_phone, load_csv_rows, merge_stores, parse_rda_centers,  # noqa: E402
                      safe_url, split_region, summarize_gap)  # noqa: E402
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
    page = http(f"https://www.data.go.kr/data/{pk}/fileData.do").decode("utf-8", "replace")
    m = re.search(r"fn_fileDataDown\('%s', '(uddi:[^']+)'" % pk, page)
    if not m:
        raise RuntimeError(f"{pk}: 다운로드 정보를 찾지 못함")
    info = json.loads(http("https://www.data.go.kr/tcs/dss/selectFileDataDownload.do", {
        "publicDataPk": pk, "publicDataDetailPk": m.group(1), "fileDetailSn": 1, "publicDataTyCode": "PR0051"}))
    raw = http("https://www.data.go.kr/cmm/cmm/fileDownload.do?" + urllib.parse.urlencode(
        {"atchFileId": info["atchFileId"], "fileDetailSn": info["fileDetailSn"]}))
    return raw, info["dataSetFileDetailInfo"]["dataNm"]


def _without_updated(obj):
    o = dict(obj)
    if isinstance(o.get("meta"), dict):
        o["meta"] = {k: v for k, v in o["meta"].items() if k != "updated"}
    return o


def write_json(path, obj):
    """임시 파일에 쓴 뒤 교체. 갱신 날짜 말고는 같으면 쓰지 않고 False."""
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                if _without_updated(json.load(f)) == _without_updated(obj):
                    return False
        except ValueError:
            pass
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)
    return True


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
                                             "name": c["name"], "tel": tel, "homepage": safe_url(c["homepage"])})
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
                      "homepage": safe_url(get("홈페이지 링크")), "products": get("대표 상품")})
    return {"meta": meta(nm), "items": items}


def _phone_count(obj):
    return sum(1 for rows in obj["by_region"].values() for r in rows if r.get("tel"))


def check_not_worse(old_path, new):
    """새로 받은 전화번호 수가 기존의 80% 미만이면 실패 (해외 IP 차단 등으로 일부만 받힌 경우)"""
    if not os.path.exists(old_path):
        return
    with open(old_path, encoding="utf-8") as f:
        old = _phone_count(json.load(f))
    if _phone_count(new) < old * 0.8:
        raise RuntimeError(f"{os.path.basename(old_path)}: 전화번호 {old} → {_phone_count(new)}개로 줄어 갱신 안 함")


def run_static(out_dir):
    results = {"contacts.json": build_contacts(), "stores.json": build_stores(), "nurseries.json": build_nurseries()}
    for name in ("contacts.json", "stores.json"):
        check_not_worse(os.path.join(out_dir, name), results[name])
    for name, obj in results.items():  # 전부 성공한 뒤에만 쓴다
        print(name, "저장" if write_json(os.path.join(out_dir, name), obj) else "변경 없음")


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


def latest_mafra_file(page):
    """농림축산식품 공공데이터 포털 상세 페이지 → (가장 최근 file_sn, 기준일 YYYY-MM-DD)"""
    best = None
    for m in re.finditer(r"filedownload\('[^']+', 'file', '(\d+)'\);\"[^>]*>[^<]*_(\d{8})\.csv<", page):
        if best is None or m.group(2) > best[1]:
            best = (m.group(1), m.group(2))
    if not best:
        raise RuntimeError("GAP 파일 목록을 찾지 못함")
    d = best[1]
    return best[0], f"{d[:4]}-{d[4:6]}-{d[6:]}"


def run_gap(out_dir):
    src = SOURCES["gap"]
    page = http(f"https://data.mafra.go.kr/opendata/data/indexOpenDataDetail.do?data_id={src['data_id']}")
    sn, as_of = latest_mafra_file(page.decode("utf-8", "replace"))
    raw = http("https://data.mafra.go.kr/opendata/data/downloadOpenDataWebFile.do",
               {"data_id": src["data_id"], "file_ty_code": "file", "file_sn": sn}, timeout=120)
    rows = load_csv_rows(raw)
    if len(rows) < 100000:
        raise RuntimeError(f"GAP 행 수가 너무 적음: {len(rows)}")
    with open(os.path.join(out_dir, "crops.json"), encoding="utf-8") as f:
        crops = json.load(f)
    by_crop = summarize_gap(rows, crops)
    changed = write_json(os.path.join(out_dir, "gap.json"), {
        "meta": {"sources": [src["name"]], "as_of": as_of, "updated": datetime.now(KST).strftime("%Y-%m-%d"),
                 "rows": len(rows)},
        "by_crop": by_crop})
    print("gap.json", "저장" if changed else "변경 없음", as_of, len(rows), "행,", len(by_crop), "작물")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
