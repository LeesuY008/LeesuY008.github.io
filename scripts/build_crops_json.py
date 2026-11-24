"""crops.json 생성: 작물 기본 정보 + 위키미디어 사진/라이선스.

작물을 추가·수정할 때 수동 실행: python3 scripts/build_crops_json.py data/crops/crops.json
"""
import json, re, sys, time, urllib.parse, urllib.request

UA = {"User-Agent": "crop-finder-builder/1.0 (static site data build)"}
# key, 이름, 분류, seed_type, 영문 위키 제목, 주산지, 별칭(추가), 설명
C = [
 ("rice","쌀","곡물","seed","Rice",["전남","충남","전북"],["벼","미곡"],"우리나라 대표 주식 작물로, 서해안 평야 지대에서 많이 재배합니다. 모내기는 5~6월, 수확은 9~10월입니다."),
 ("barley","보리","곡물","seed","Barley",["전북","전남"],["겉보리","쌀보리","맥주보리"],"가을에 심어 이듬해 초여름에 거두는 겨울 작물입니다. 남부 지방 논에서 벼 뒷그루로 많이 재배합니다."),
 ("wheat","밀","곡물","seed","Wheat",["전북","전남","경남"],["우리밀"],"보리처럼 가을에 심어 초여름에 수확합니다. 국산 밀은 주로 호남 지역에서 생산됩니다."),
 ("soybean","콩","곡물","seed","Soybean",["경북","충남","전북"],["대두","서리태","백태"],"된장·두부의 원료로, 밭이나 논두렁에서 재배합니다. 가을에 수확합니다."),
 ("adzuki","팥","곡물","seed","Vigna angularis",["강원","충북","경북"],["적두"],"떡과 빵 소에 쓰이는 콩과 작물로, 서늘한 산간 지역에서 많이 재배합니다."),
 ("corn","옥수수","곡물","seed","Maize",["강원","충북"],["찰옥수수","초당옥수수"],"여름철 간식용 찰옥수수는 강원도 홍천·정선, 충북 괴산이 유명합니다."),
 ("potato","감자","곡물","seed","Potato",["강원","제주","경북"],["수미"],"강원 고랭지와 제주에서 많이 나며, 봄·여름·가을 작형이 있습니다. 씨감자로 번식합니다."),
 ("sweetpotato","고구마","곡물","seed","Sweet potato",["전남","충남","경기"],["호박고구마","밤고구마"],"모종(순)을 심어 가을에 수확합니다. 전남 해남, 경기 여주가 유명합니다."),
 ("buckwheat","메밀","곡물","seed","Buckwheat",["강원","제주"],[],"서늘하고 척박한 땅에서도 잘 자랍니다. 제주가 최대 산지이고 강원 평창 봉평이 유명합니다."),
 ("peanut","땅콩","곡물","seed","Peanut",["전북","경기"],["낙화생"],"모래가 섞인 밭에서 잘 자라며 가을에 수확합니다. 전북 고창, 경기 여주가 주산지입니다."),
 ("napacabbage","배추","채소","seed","Napa cabbage",["강원","전남","충북"],["절임배추","봄배추","고랭지배추"],"김치의 주재료입니다. 여름에는 강원 고랭지, 겨울에는 전남 해남 등에서 나옵니다."),
 ("radish","무","채소","seed","Daikon",["강원","제주","전남"],["월동무","알타리무","총각무"],"여름 고랭지 무는 강원, 겨울 월동무는 제주에서 주로 나옵니다."),
 ("chili","고추","채소","seed","Chili pepper",["경북","충북","전남"],["건고추","풋고추","청양고추","홍고추"],"고춧가루용 건고추는 경북 영양·안동, 충북 괴산·음성이 대표 산지입니다."),
 ("garlic","마늘","채소","seed","Garlic",["경북","경남","충남","제주"],["난지형마늘","한지형마늘","깐마늘"],"가을에 씨마늘을 심어 이듬해 초여름에 수확합니다. 의성·서산·남해·제주가 유명합니다."),
 ("onion","양파","채소","seed","Onion",["전남","경남"],["조생양파","만생양파"],"가을에 모종을 심어 봄~초여름에 수확합니다. 전남 무안, 경남 창녕이 주산지입니다."),
 ("greenonion","대파","채소","seed","Welsh onion",["전남","경기"],["파","쪽파"],"사계절 나오는 양념 채소로, 겨울 대파는 전남 진도·신안이 주산지입니다."),
 ("carrot","당근","채소","seed","Carrot",["제주","부산"],[],"겨울 당근은 제주 구좌 지역이 국내 최대 산지입니다."),
 ("cabbage","양배추","채소","seed","Cabbage",["제주","강원"],["캐비지"],"겨울에는 제주, 여름에는 강원 고랭지에서 주로 생산됩니다."),
 ("cucumber","오이","채소","seed","Cucumber",["충남","경기","전남"],["백다다기","취청오이"],"시설 하우스에서 연중 재배합니다. 충남 천안, 경기 지역이 주요 산지입니다."),
 ("squash","호박","채소","seed","Cucurbita",["경기","강원","전남"],["애호박","단호박","늙은호박","주키니"],"애호박과 단호박, 늙은호박 등 종류가 다양합니다."),
 ("tomato","토마토","채소","seed","Tomato",["충남","경남","전북"],["방울토마토","대추방울토마토","대저토마토"],"시설 재배가 중심입니다. 부여·진주·부산 대저가 유명합니다."),
 ("paprika","파프리카","채소","seed","Bell pepper",["경남","전남","강원"],["피망"],"대부분 유리온실에서 재배하며 경남 진주, 강원 철원 등에서 생산합니다."),
 ("spinach","시금치","채소","seed","Spinach",["전남","경남"],["포항초","섬초"],"겨울 노지 시금치는 전남 신안 섬초, 경북 포항초가 유명합니다."),
 ("lettuce","상추","채소","seed","Lettuce",["경기","충남"],["적상추","청상추","양상추"],"수도권 근교에서 하우스로 연중 재배합니다."),
 ("eggplant","가지","채소","seed","Eggplant",["경기","전남","경남"],[],"여름 대표 채소로 시설과 노지 모두에서 재배합니다."),
 ("ginger","생강","채소","seed","Ginger",["충남","전북"],[],"충남 서산·태안과 전북 완주 봉동이 대표 산지입니다."),
 ("broccoli","브로콜리","채소","seed","Broccoli",["제주","강원"],["녹색꽃양배추"],"겨울에는 제주, 여름에는 강원 고랭지에서 주로 생산됩니다."),
 ("chives","부추","채소","seed","Allium tuberosum",["경북","경기"],["정구지","솔부추"],"한 번 심으면 여러 번 베어 수확합니다. 경북 포항, 경기 지역이 주요 산지입니다."),
 ("apple","사과","과일","tree","Apple",["경북","충북","강원"],["부사","후지","홍로","감홍"],"경북 영주·청송·안동이 최대 산지이며, 기후 변화로 강원 양구·정선까지 재배지가 넓어졌습니다."),
 ("pear","배","과일","tree","Pyrus pyrifolia",["전남","충남","경기"],["신고","원황","화산"],"전남 나주, 충남 천안, 경기 안성이 대표 산지입니다."),
 ("mandarin","감귤","과일","tree","Satsuma mandarin",["제주"],["귤","밀감","온주밀감","하우스감귤"],"제주의 대표 과일로 노지·하우스·월동 감귤이 있습니다."),
 ("hallabong","한라봉","과일","tree","Dekopon",["제주"],["부지화","천혜향","레드향","황금향"],"제주에서 시설 재배하는 만감류로, 한라봉·천혜향·레드향 등이 있습니다."),
 ("grape","포도","과일","tree","Grape",["경북","충북","경기"],["샤인머스캣","캠벨얼리","거봉"],"경북 김천·상주·영천, 충북 영동, 경기 안성이 주요 산지입니다."),
 ("peach","복숭아","과일","tree","Peach",["경북","충북"],["백도","황도","천도복숭아"],"경북 청도·영덕, 충북 음성·충주가 유명합니다."),
 ("persimmon","단감","과일","tree","Persimmon",["경남","전남"],["감","대봉","곶감","떫은감"],"단감은 경남 창원·김해·진주, 곶감용 떫은감은 경북 상주·청도가 주산지입니다."),
 ("koreanmelon","참외","과일","seed","Korean melon",["경북"],[],"경북 성주가 전국 생산의 대부분을 차지합니다. 하우스에서 재배합니다."),
 ("watermelon","수박","과일","seed","Watermelon",["충남","전북","경남"],["애플수박"],"충남 논산·부여, 전북 고창, 경남 함안이 대표 산지입니다."),
 ("strawberry","딸기","과일","seed","Strawberry",["충남","경남","전남"],["설향","금실","킹스베리"],"겨울~봄 하우스에서 재배합니다. 충남 논산, 경남 진주·밀양, 전남 담양이 유명합니다."),
 ("blueberry","블루베리","과일","tree","Blueberry",["전북","전남","경기"],[],"묘목을 심어 2~3년 뒤부터 수확합니다. 전북 고창·정읍 등에서 많이 재배합니다."),
 ("maesil","매실","과일","tree","Prunus mume",["전남","경남"],["청매","황매","매화"],"전남 광양, 경남 하동·순천이 유명하며 6월에 수확합니다."),
 ("plum","자두","과일","tree","Plum",["경북"],["추희","대석"],"경북 김천과 의성이 주산지로, 여름에 수확합니다."),
 ("kiwi","키위","과일","tree","Kiwifruit",["전남","경남","제주"],["참다래","골드키위"],"따뜻한 남해안과 제주에서 재배합니다."),
 ("rubus","복분자","과일","tree","Rubus coreanus",["전북","전남"],["복분자딸기"],"전북 고창·정읍이 대표 산지이며, 덩굴성 나무 묘목으로 심습니다."),
 ("chestnut","밤","과일","tree","Castanea crenata",["충남","전남","경남"],["알밤"],"충남 공주·부여, 전남 광양, 경남 하동·산청이 주요 산지입니다."),
 ("jujube","대추","과일","tree","Jujube",["충북","경북"],["건대추","사과대추"],"충북 보은, 경북 경산·밀양이 유명합니다."),
 ("yuzu","유자","과일","tree","Yuzu",["전남","경남"],[],"전남 고흥, 경남 거제·남해 등 따뜻한 남해안에서 재배합니다."),
 ("walnut","호두","과일","tree","Juglans regia",["충남","경북","충북"],[],"충남 천안, 경북 김천, 충북 영동이 주요 산지입니다."),
 ("ginseng","인삼","특용작물","seed","Panax ginseng",["충남","경북","경기","강원"],["수삼","홍삼","묘삼"],"차광막 아래에서 4~6년 키웁니다. 충남 금산, 경북 영주 풍기, 경기 이천·강화가 유명합니다."),
 ("tea","녹차","특용작물","tree","Camellia sinensis",["전남","경남","제주"],["차","차나무","찻잎"],"전남 보성, 경남 하동, 제주에서 재배합니다. 차나무 묘목으로 심습니다."),
 ("shiitake","표고버섯","특용작물","seed","Shiitake",["충남","전남","경북"],["표고","생표고","건표고"],"참나무 원목이나 톱밥 배지에 종균을 넣어 키웁니다. 충남 부여·청양, 전남 장흥이 유명합니다."),
 ("sesame","참깨","특용작물","seed","Sesame",["경북","전남"],["깨"],"여름에 꽃이 피고 가을에 수확하는 기름 작물입니다."),
 ("perilla","들깨","특용작물","seed","Perilla frutescens",["충북","경북","강원"],["깻잎","들깻잎"],"잎은 깻잎으로, 씨는 들기름으로 씁니다. 깻잎은 충남 금산, 경남 밀양이 유명합니다."),
 ("schisandra","오미자","특용작물","tree","Schisandra chinensis",["경북","강원","전북"],[],"덩굴성 나무로 경북 문경, 강원 인제, 전북 장수가 주산지입니다."),
]


# 위키백과 대표 이미지가 식물 도감 그림이거나 열매가 잘 안 보이는 작물은 실제 사진 파일로 바꾼다 (2026-11-24 선정)
PHOTO_OVERRIDE = {"corn": "File:Corn on the cob half open.jpg", "peanut": "File:Roasted Peanuts with shell.jpg", "garlic": "File:Garlic bulbs and cloves.jpg", "ginger": "File:Ginger rhizome.jpg", "peach": "File:Peach fruit 3.jpg", "sesame": "File:Sa white sesame seeds.jpg", "jujube": "File:DFC 3955 A close-up pile of ripe jujube fruits showing their mottled brown and yellow skins.jpg", "chestnut": "File:Frucht der Edelkastanie.jpg", "walnut": "File:Juglans regia nuts, apex and base.jpg", "schisandra": "File:Omija.jpg"}


def get(url):
    for n in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
                return json.load(r)
        except Exception as e:
            last = e; time.sleep(10 * (n + 1))
    raise last


def strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()



def batch(api, params, titles):
    res, rmap = {}, {}
    for i in range(0, len(titles), 25):
        q = urllib.parse.urlencode(dict(params, format="json", titles="|".join(titles[i:i + 25])))
        body = get(api + "?" + q)
        if "query" not in body:
            raise SystemExit(f"API 오류: {body.get('error')}")
        data = body["query"]
        for r in data.get("normalized", []) + data.get("redirects", []):
            rmap[r["from"]] = r["to"]
        for pg in data["pages"].values():
            res[pg["title"]] = pg
        time.sleep(2)
    return res, rmap

pages, rmap = batch("https://en.wikipedia.org/w/api.php",
                    {"action": "query", "prop": "pageimages", "piprop": "name", "pilimit": 50, "redirects": 1},
                    [c[4] for c in C])
def resolve(t):
    seen = 0
    while t in rmap and seen < 5:
        t = rmap[t]; seen += 1
    return t
fnames = {c[4]: pages.get(resolve(c[4]), {}).get("pageimage") for c in C}
for c in C:
    if c[0] in PHOTO_OVERRIDE:
        fnames[c[4]] = PHOTO_OVERRIDE[c[0]].removeprefix("File:").replace(" ", "_")
time.sleep(3)
files = ["File:" + f for f in fnames.values() if f]
infos, frmap = batch("https://commons.wikimedia.org/w/api.php",
                     {"action": "query", "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": 640}, files)
out = []
for key, name, cat, st, title, regions, extra, desc in C:
    f = fnames.get(title)
    if not f:
        print("NO IMAGE", name, title, file=sys.stderr); continue
    ft = "File:" + f
    ft = frmap.get(ft, ft)
    info = infos.get(ft, {})
    if "imageinfo" not in info:
        print("NOT ON COMMONS", name, f, file=sys.stderr); continue
    ii = info["imageinfo"][0]; md = ii.get("extmetadata", {})
    out.append({"key": key, "name": name, "category": cat, "desc": desc, "main_regions": regions,
                "aliases": [name] + extra, "seed_type": st,
                "photo": {"url": (ii.get("thumburl") or ii["url"]).split("?")[0],
                          "author": re.sub(r"\s+", " ", re.sub(r"\S+ \[at\] \S+", "", strip_html(md.get("Artist", {}).get("value")))).strip()[:120],
                          "license": strip_html(md.get("LicenseShortName", {}).get("value")),
                          "page": ii["descriptionurl"]}})
# GAP 품목 이름과 대조해 보탠 별칭·제외어 (2026-09-14 자료 기준)
EXTRA = {"rice": {"aliases": ["찰벼", "찹쌀"]}, "grape": {"aliases": ["샤인마스캇", "청포도", "머루포도"]}, "hallabong": {"aliases": ["만감"]}, "tomato": {"aliases": ["대추방울"]}, "strawberry": {"exclude": ["산딸기"]}, "chili": {"exclude": ["고추냉이"]}, "potato": {"exclude": ["돼지감자"]}, "garlic": {"exclude": ["산마늘"]}, "broccoli": {"aliases": ["브로코리"]}}
for c in out:
    e = EXTRA.get(c["key"], {})
    c["aliases"] += [a for a in e.get("aliases", []) if a not in c["aliases"]]
    if e.get("exclude"):
        c["exclude"] = e["exclude"]
# 위키미디어 사진을 잘라 저장소에 둔 경우 (CC 라이선스 범위에서 일부 확대)
LOCAL_PHOTO = {"rubus": {"url": "images/crops/rubus.jpg", "note": "열매 부분 확대"}}
for c in out:
    if c["key"] in LOCAL_PHOTO:
        c["photo"].update(LOCAL_PHOTO[c["key"]])
json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(out), "crops")
