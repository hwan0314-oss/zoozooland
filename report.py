import asyncio
import io
import json
import math
import os
import re
from datetime import date, timedelta, datetime, timezone

import requests
import telegram
import urllib3
from PIL import Image, ImageDraw, ImageFont

urllib3.disable_warnings()

BASE_URL  = "https://kis.okpos.co.kr"
API_URL   = BASE_URL + "/sale/sale/ddd.htmlSheetAction"

USER_ID   = os.environ["KIS_ID"]
USER_PW   = os.environ["KIS_PW"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID   = -1003990713280

KST = timezone(timedelta(hours=9))
KMA_API_KEY = os.environ.get("KMA_API_KEY", "")

FOOD_KEYWORDS  = ["먹이", "양분유체험"]
# 외부 플랫폼(네이버 스마트플레이스 / LS파트너) 결제 상품:
#   - OKPOS에는 qty만 기록, TOT_SALE_AMT = 0 (대사 목적 0원 상품)
#   - 실제 정산금액은 각 플랫폼에서 별도 집계
NAVER_TICKETS  = {"네이버 주중", "네이버 주말"}
LS_TICKETS     = {"온라인티켓(LS)"}
ONLINE_TICKETS = NAVER_TICKETS | LS_TICKETS  # 매출 ₩0, 입장수량은 개인으로 집계
FREE_PRODUCTS  = {"24개월미만무료입장", "초대권"}

ZOOZOOLAND_LAT = 37.6899
ZOOZOOLAND_LON = 126.8547
KMA_ASOS_STN   = 108  # 서울 ASOS 관측소 (전년 날씨 조회용)
WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]
WMO_WEATHER = {
    0: "맑음", 1: "대체로맑음", 2: "구름조금", 3: "흐림",
    45: "안개", 48: "안개",
    51: "이슬비", 53: "이슬비", 55: "이슬비",
    61: "비", 63: "비", 65: "강한비",
    71: "눈", 73: "눈", 75: "강한눈", 77: "눈",
    80: "소나기", 81: "소나기", 82: "강한소나기",
    95: "뇌우", 96: "뇌우", 99: "뇌우",
}

STORE_KEYS = [
    ("레스토랑",     "레스토랑"),
    ("카페테리아",   "카페테리아"),
    ("레스토랑신규", "레스토랑(신)"),
    ("무인점포",     "무인점포"),
    ("드론체험",     "드론체험"),
    ("베이커리",     "베이커리"),
]

S_SAVENAME = (
    "sSeq|LCLS_NM|MCLS_NM|SCLS_NM|SALE_DATE|PROD_CD|BAR_CD|MAP_PROD_CD"
    "|PROD_NM|VENDORS_NM|COLOR_CD|SIZE_STR_CD|SALE_QTY|PROD_WEIGHT"
    "|TOT_SALE_AMT|TOT_DC_AMT|DCM_SALE_AMT|DC_AMT_GEN|DC_AMT_SVC"
    "|DC_AMT_JCD|DC_AMT_CPN|DC_AMT_CST|DC_AMT_FOD|DC_AMT_PACK"
    "|DC_AMT_YAP|SHOP_CD"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# ─── Image style constants ────────────────────────────────────────────────────
FONT_REGULAR = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_BOLD    = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"

C_TITLE_BG  = ( 30,  45,  60)
C_PERIOD_BG = ( 44,  62,  80)
C_COL_BG    = ( 58,  79,  99)
C_ROW_ODD   = (255, 255, 255)
C_ROW_EVEN  = (245, 248, 251)
C_ROW_TOTAL = (230, 242, 252)
C_SEP_ROW   = (173, 186, 199)
C_BORDER    = (180, 192, 205)
C_P_BORDER  = ( 90, 120, 155)   # thicker border between period groups
C_WHITE     = (255, 255, 255)
C_TEXT      = ( 44,  62,  80)
C_SUB       = ( 90, 110, 130)
C_POS       = ( 39, 174,  96)
C_NEG       = (192,  57,  43)
C_NA        = (127, 140, 141)


# ─── Login / session ──────────────────────────────────────────────────────────

def extract_token(html):
    m = re.search(
        r"id='([0-9a-f-]{36})'\s+name='([0-9a-f-]{36})'\s+value='([0-9a-f-]{36})'",
        html, re.IGNORECASE,
    )
    if m:
        return m.group(2), m.group(3)
    m = re.search(r'name="([0-9a-f-]{36})"[^>]*value="([0-9a-f-]{36})"', html, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r'name="([0-9a-f-]{36})"[^>]*value="([^"]+)"', html, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r"name='([0-9a-f-]{36})'[^>]*value='([^']+)'", html, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2)
    return None, None


def do_login():
    sess = requests.Session()
    sess.headers.update(HEADERS)
    r0 = sess.get(BASE_URL + "/login/login_form.jsp", verify=False, timeout=30)
    print(f"login_form: {r0.status_code} len={len(r0.text)}")
    form_tok_n, form_tok_v = extract_token(r0.text)
    print(f"form token: {form_tok_n[:8] if form_tok_n else None}...")
    login_data = {"user_id": USER_ID, "user_pwd": USER_PW, "AutoFg": "W"}
    if form_tok_n:
        login_data[form_tok_n] = form_tok_v
    r1 = sess.post(
        BASE_URL + "/login/login_check.jsp", data=login_data,
        headers={"Referer": BASE_URL + "/login/login_form.jsp"}, verify=False, timeout=30,
    )
    print(f"login_check: {r1.status_code} len={len(r1.text)}")
    tok_name, tok_val = extract_token(r1.text)
    if not tok_name:
        raise RuntimeError(f"No CSRF token. HTML: {r1.text[:300]}")
    print(f"CSRF: {tok_name[:8]}...")
    r2 = sess.post(
        BASE_URL + "/login/login_check_action.jsp",
        data={"user_id": USER_ID, "user_pwd": USER_PW, "AutoFg": "W", tok_name: tok_val},
        headers={"Referer": BASE_URL + "/login/login_check.jsp"}, verify=False, timeout=30,
    )
    print(f"login_action: {r2.status_code} len={len(r2.text)}")
    if "top_frame" not in r2.text:
        raise RuntimeError(f"Login failed. Response: {r2.text[:200]}")
    sess.get(BASE_URL + "/login/top_frame.jsp", verify=False, timeout=30)
    print("Login OK!")
    return sess


def get_api_token(sess):
    r1 = sess.get(
        BASE_URL + "/sale/sale/prod010.jsp",
        headers={"Referer": BASE_URL + "/login/top_frame.jsp"}, verify=False, timeout=30,
    )
    print(f"prod010: {r1.status_code} len={len(r1.text)}")
    tok10n, tok10v = extract_token(r1.text)
    if not tok10n:
        raise RuntimeError(f"No token in prod010. HTML: {r1.text[:300]}")
    r2 = sess.post(
        BASE_URL + "/sale/sale/prod011.jsp", data={tok10n: tok10v},
        headers={"Referer": BASE_URL + "/sale/sale/prod010.jsp"}, verify=False, timeout=30,
    )
    print(f"prod011: {r2.status_code} len={len(r2.text)}")
    if "S_CONTROLLER" not in r2.text:
        raise RuntimeError(f"prod011 bad response. First 200: {r2.text[:200]}")
    tok11n, tok11v = extract_token(r2.text)
    if not tok11n:
        raise RuntimeError("No token in prod011")
    print(f"prod011 token: {tok11n[:8]}...")
    return tok11n, tok11v


# ─── Sales data fetching ──────────────────────────────────────────────────────

def fetch_sales(sess, tok_name, tok_val, date_from, date_to):
    payload = {
        tok_name: tok_val,
        "S_CONTROLLER": "sale.sale.prod011", "S_METHOD": "search",
        "SHEETSEQ": "1", "S_SAVENAME": S_SAVENAME, "S_ORDERBY": "",
        "ss_PROD_FG": "N", "date1_1": date_from, "date1_2": date_to,
        "date_period1": "366",
        "ss_PROD_CD": "", "ss_PROD_NM": "",
        "ss_LCLS_CD": "", "ss_MCLS_CD": "", "ss_SCLS_CD": "", "ss_SIZE_CLS_CD": "",
        "ss_CLS_TEXT": "전체", "ss_BAR_CD": "", "ss_SHOP_CD": "",
        "ss_SHOP_NM": "전체", "ss_SHOP_INFO": "[]",
        "ss_VENDOR_CD": "", "ss_VENDOR_NM": "전체", "ss_VENDOR_INFO": "[]",
        "ss_chk": "0", "ss_PAGE_SIZE": "500", "ss_PAGE_NO1": "1",
    }
    r = sess.post(API_URL, data=payload,
                  headers={"Referer": BASE_URL + "/sale/sale/prod011.jsp"},
                  verify=False, timeout=60)
    print(f"API [{date_from}~{date_to}]: {r.status_code} len={len(r.text)}")
    data = json.loads(r.text)
    if "Result" in data and data["Result"].get("Code", 0) < 0:
        raise RuntimeError(f"API error: {data['Result']['Message']}")
    rows = data.get("Data", [])

    cats      = {}
    food      = {"qty": 0, "amt": 0}
    admission = {"individual": 0, "group": 0, "free": 0}
    # 외부정산 온라인 티켓 수량 별도 집계 (매출 ₩0, 실적 파악용)
    online    = {"naver": 0, "ls": 0}

    for row in rows:
        cat     = row.get("MCLS_NM") or row.get("LCLS_NM") or "기타"
        prod_nm = (row.get("PROD_NM") or "").strip()
        scls_nm = (row.get("SCLS_NM") or "").strip()
        qty     = int(row.get("SALE_QTY", 0) or 0)
        # 온라인 티켓: OKPOS TOT_SALE_AMT = 0(외부결제) → 가짜 금액 없이 0 그대로 사용
        amt     = int(row.get("TOT_SALE_AMT", 0) or 0)

        if cat not in cats:
            cats[cat] = {"qty": 0, "amt": 0}
        cats[cat]["qty"] += qty
        cats[cat]["amt"] += amt

        if any(kw in prod_nm for kw in FOOD_KEYWORDS):
            food["qty"] += qty
            food["amt"] += amt

        if cat == "매표소":
            if prod_nm in FREE_PRODUCTS:
                admission["free"] += qty
            elif "단체" in scls_nm or "단체" in prod_nm:
                admission["group"] += qty
            else:
                # 개인 + 온라인티켓(SCLS_NM이 "개인"이 아닐 수 있으므로 else로 포괄)
                # 온라인티켓은 외부결제이므로 단체·무료가 아닌 이상 개인 입장자로 집계
                admission["individual"] += qty

        if prod_nm in NAVER_TICKETS:
            online["naver"] += qty
        elif prod_nm in LS_TICKETS:
            online["ls"] += qty

    print(f"  Categories: {list(cats.keys())}")
    print(f"  Online qty: naver={online['naver']}, ls={online['ls']}")
    return {"cats": cats, "food": food, "admission": admission, "online": online}


def fetch_sales_chunked(sess, date_from_str, date_to_str, max_days=90):
    start = date.fromisoformat(date_from_str)
    end   = date.fromisoformat(date_to_str)
    total = {
        "cats": {},
        "food": {"qty": 0, "amt": 0},
        "admission": {"individual": 0, "group": 0, "free": 0},
        "online": {"naver": 0, "ls": 0},
    }
    current = start
    while current <= end:
        chunk_end = min(current + timedelta(days=max_days - 1), end)
        tn, tv = get_api_token(sess)
        chunk = fetch_sales(sess, tn, tv, current.isoformat(), chunk_end.isoformat())
        for cat, vals in chunk["cats"].items():
            if cat not in total["cats"]:
                total["cats"][cat] = {"qty": 0, "amt": 0}
            total["cats"][cat]["qty"] += vals["qty"]
            total["cats"][cat]["amt"] += vals["amt"]
        total["food"]["qty"] += chunk["food"]["qty"]
        total["food"]["amt"] += chunk["food"]["amt"]
        for k in ("individual", "group", "free"):
            total["admission"][k] += chunk["admission"][k]
        for k in ("naver", "ls"):
            total["online"][k] += chunk["online"][k]
        current = chunk_end + timedelta(days=1)
    return total


# ─── Data helpers ─────────────────────────────────────────────────────────────

def yoy(curr, prev):
    if not prev:
        return None
    return (curr - prev) / prev * 100

def fmt_num(n):
    return f"{int(n):,}"

def fyoy(v):
    if v is None:
        return "N/A"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.1f}%"


def nearest_same_weekday_last_year(today):
    """전년 중 today와 가장 가까운 동일 요일 날짜 반환."""
    base = today.replace(year=today.year - 1)
    diff = (today.weekday() - base.weekday()) % 7
    if diff > 3:
        diff -= 7
    return base + timedelta(days=diff)


def latlon_to_kma_grid(lat, lon):
    """위경도 → 기상청 격자 좌표(nx, ny) 변환."""
    RE, GRID = 6371.00877, 5.0
    SLAT1, SLAT2, OLON, OLAT, XO, YO = 30.0, 60.0, 126.0, 38.0, 43, 136
    d = math.pi / 180.0
    re = RE / GRID
    sn = math.log(math.cos(SLAT1 * d) / math.cos(SLAT2 * d)) / \
         math.log(math.tan(math.pi * 0.25 + SLAT2 * d * 0.5) /
                  math.tan(math.pi * 0.25 + SLAT1 * d * 0.5))
    sf = (math.tan(math.pi * 0.25 + SLAT1 * d * 0.5) ** sn) * math.cos(SLAT1 * d) / sn
    ro = re * sf / (math.tan(math.pi * 0.25 + OLAT * d * 0.5) ** sn)
    ra = re * sf / (math.tan(math.pi * 0.25 + lat * d * 0.5) ** sn)
    theta = (lon - OLON) * d * sn
    return round(ra * math.sin(theta) + XO), round(ro - ra * math.cos(theta) + YO)


def get_weather(target_date):
    """날씨 조회. KMA API 우선, 실패 시 Open-Meteo fallback."""
    fmt = target_date.strftime("%Y-%m-%d")
    today_kst = datetime.now(KST).date()
    try:
        if target_date >= today_kst:
            return _get_weather_kma() if KMA_API_KEY else _get_weather_openmeteo_today()
        else:
            return _get_weather_kma_archive(fmt) if KMA_API_KEY else _get_weather_openmeteo_archive(fmt)
    except Exception as e:
        print(f"Weather fetch failed ({fmt}): {e}")
        # fallback
        try:
            if target_date >= today_kst:
                return _get_weather_openmeteo_today()
            else:
                return _get_weather_openmeteo_archive(fmt)
        except Exception:
            return "", "--", "--"


def _get_weather_kma():
    """기상청 공공API: 초단기실황(현재기온/강수) + 단기예보(최고/최저/하늘)."""
    now  = datetime.now(KST)
    nx, ny = latlon_to_kma_grid(ZOOZOOLAND_LAT, ZOOZOOLAND_LON)
    print(f"  KMA grid: nx={nx}, ny={ny}")
    base_date = now.strftime("%Y%m%d")

    # 초단기실황 (현재 기온 T1H, 강수형태 PTY)
    ncst_h = now.hour if now.minute >= 45 else max(now.hour - 1, 0)
    r_ncst = requests.get(
        "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst",
        params={"serviceKey": KMA_API_KEY, "numOfRows": 10, "pageNo": 1,
                "dataType": "JSON", "base_date": base_date,
                "base_time": f"{ncst_h:02d}00", "nx": nx, "ny": ny},
        timeout=15,
    )
    t1h, pty = None, 0
    for it in r_ncst.json()["response"]["body"]["items"]["item"]:
        if it["category"] == "T1H": t1h = float(it["obsrValue"])
        if it["category"] == "PTY": pty = int(float(it["obsrValue"]))
    print(f"  KMA Ncst: T1H={t1h}, PTY={pty}")

    # 단기예보 (일 최고/최저 TMX/TMN, 하늘상태 SKY)
    # base_time=0200 고정 → TMX(fcstTime=1500), TMN(fcstTime=0600) 항상 포함
    fcst_h = 2
    r_fcst = requests.get(
        "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst",
        params={"serviceKey": KMA_API_KEY, "numOfRows": 300, "pageNo": 1,
                "dataType": "JSON", "base_date": base_date,
                "base_time": f"{fcst_h:02d}00", "nx": nx, "ny": ny},
        timeout=15,
    )
    tmx = tmn = sky = None
    sky_map = {}
    for it in r_fcst.json()["response"]["body"]["items"]["item"]:
        if it["fcstDate"] != base_date:
            continue
        cat = it["category"]
        if cat == "TMX": tmx = float(it["fcstValue"])
        elif cat == "TMN": tmn = float(it["fcstValue"])
        elif cat == "SKY": sky_map[it["fcstTime"]] = int(it["fcstValue"])
    # 현재 시각에 가장 가까운 하늘상태
    if sky_map:
        sky = sky_map.get(f"{now.hour:02d}00") or \
              sky_map[min(sky_map, key=lambda t: abs(int(t[:2]) - now.hour))]
    print(f"  KMA Fcst: TMX={tmx}, TMN={tmn}, SKY={sky}")

    if pty == 1: desc = "비"
    elif pty == 2: desc = "비/눈"
    elif pty == 3: desc = "눈"
    elif pty == 4: desc = "소나기"
    elif sky == 1: desc = "맑음"
    elif sky == 3: desc = "구름많음"
    elif sky == 4: desc = "흐림"
    else: desc = ""

    tmax_s = f"{tmx:.0f}" if tmx is not None else (f"{t1h:.0f}" if t1h is not None else "--")
    tmin_s = f"{tmn:.0f}" if tmn is not None else "--"
    return desc, tmax_s, tmin_s


def _get_weather_openmeteo_today():
    """Open-Meteo 현재 실황 (KMA 키 없을 때 fallback)."""
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={ZOOZOOLAND_LAT}&longitude={ZOOZOOLAND_LON}"
        f"&current_weather=true&daily=temperature_2m_max,temperature_2m_min"
        f"&timezone=Asia/Seoul&forecast_days=1"
    )
    r = requests.get(url, timeout=15)
    data  = r.json()
    code  = data.get("current_weather", {}).get("weathercode")
    daily = data.get("daily", {})
    tmax  = daily.get("temperature_2m_max", [None])[0]
    tmin  = daily.get("temperature_2m_min", [None])[0]
    desc  = WMO_WEATHER.get(int(code) if code is not None else -1, "")
    return desc, (f"{tmax:.0f}" if tmax is not None else "--"), (f"{tmin:.0f}" if tmin is not None else "--")


def _get_weather_kma_archive(fmt):
    """기상청 ASOS 일자료로 과거 날씨 조회."""
    r = requests.get(
        "http://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList",
        params={
            "serviceKey": KMA_API_KEY,
            "pageNo": 1, "numOfRows": 1, "dataType": "JSON",
            "dataCd": "ASOS", "dateCd": "DAY",
            "startDt": fmt.replace("-", ""), "endDt": fmt.replace("-", ""),
            "stnIds": KMA_ASOS_STN,
        },
        timeout=15,
    )
    items = r.json()["response"]["body"].get("items", {})
    if not items or not items.get("item"):
        return "", "--", "--"
    item = items["item"]
    if isinstance(item, list):
        item = item[0]

    tmax    = item.get("maxTa")
    tmin    = item.get("minTa")
    avg_tmp = float(item.get("avgTa") or 0)
    sum_rn  = float(item.get("sumRn") or 0)
    avg_tca = float(item.get("avgTca") or 5)   # 전운량 0~10
    ddmes   = float(item.get("ddMes") or 0)    # 신적설

    if sum_rn > 0:
        desc = "눈" if avg_tmp <= 2 else "비"
    elif ddmes > 0:
        desc = "눈"
    elif avg_tca <= 2:
        desc = "맑음"
    elif avg_tca <= 5:
        desc = "구름조금"
    elif avg_tca <= 8:
        desc = "구름많음"
    else:
        desc = "흐림"

    return desc, (f"{float(tmax):.0f}" if tmax else "--"), (f"{float(tmin):.0f}" if tmin else "--")


def _get_weather_openmeteo_archive(fmt):
    """Open-Meteo 과거 날씨 (전년 비교용)."""
    url = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={ZOOZOOLAND_LAT}&longitude={ZOOZOOLAND_LON}"
        f"&daily=temperature_2m_max,temperature_2m_min,weathercode"
        f"&timezone=Asia/Seoul&start_date={fmt}&end_date={fmt}"
    )
    r     = requests.get(url, timeout=15)
    daily = r.json().get("daily", {})
    tmax  = daily.get("temperature_2m_max", [None])[0]
    tmin  = daily.get("temperature_2m_min", [None])[0]
    code  = daily.get("weathercode", [None])[0]
    desc  = WMO_WEATHER.get(int(code) if code is not None else -1, "")
    return desc, (f"{tmax:.0f}" if tmax is not None else "--"), (f"{tmin:.0f}" if tmin is not None else "--")


def _section_data(curr, prev):
    """(label, val_str, yoy_str) 리스트. None 은 구분선."""
    cats_c = curr["cats"];  cats_p = prev["cats"]
    fa     = curr["food"]["amt"]; pfa = prev["food"]["amt"]
    adm_c  = curr["admission"]; adm_p = prev["admission"]

    ind_c = adm_c["individual"]; ind_p = adm_p["individual"]
    grp_c = adm_c["group"];      grp_p = adm_p["group"]
    fre_c = adm_c["free"];       fre_p = adm_p["free"]
    tot_c = ind_c + grp_c + fre_c
    tot_p = ind_p + grp_p + fre_p

    tc, tp = 0, 0
    store_rows = []
    for k, lbl in STORE_KEYS:
        ca = cats_c.get(k, {}).get("amt", 0)
        pa = cats_p.get(k, {}).get("amt", 0)
        tc += ca; tp += pa
        store_rows.append((f"  {lbl}", f"{fmt_num(ca)}원", fyoy(yoy(ca, pa))))

    all_c = sum(v["amt"] for v in cats_c.values())
    all_p = sum(v["amt"] for v in cats_p.values())

    return [
        ("입장(전체)", f"{fmt_num(tot_c)}명", fyoy(yoy(tot_c, tot_p))),
        ("  개인",     f"{fmt_num(ind_c)}명", fyoy(yoy(ind_c, ind_p))),
        ("  단체",     f"{fmt_num(grp_c)}명", fyoy(yoy(grp_c, grp_p))),
        ("  무료",     f"{fmt_num(fre_c)}명", fyoy(yoy(fre_c, fre_p))),
        None,
        ("먹이판매",   f"{fmt_num(fa)}원",    fyoy(yoy(fa, pfa))),
        None,
        *store_rows,
        ("  점포합계", f"{fmt_num(tc)}원",    fyoy(yoy(tc, tp))),
        None,
        # 전체매출: 온라인티켓은 OKPOS에 ₩0으로 등록(외부정산)이므로 이미 제외된 실집계
        ("전체매출",   f"{fmt_num(all_c)}원", fyoy(yoy(all_c, all_p))),
    ]


# ─── Image rendering ──────────────────────────────────────────────────────────

def _load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except (IOError, OSError):
        return ImageFont.load_default()

def _yoy_color(s):
    if s == "N/A":        return C_NA
    if s.startswith("+"): return C_POS
    if s.startswith("-"): return C_NEG
    return C_TEXT


def create_report_image(today, ptd, weather_today, weather_ptd, dc, dp, mc, mp, yc, yp):
    fnt_r = _load_font(FONT_REGULAR, 14)
    fnt_b = _load_font(FONT_BOLD,    14)
    fnt_s = _load_font(FONT_REGULAR, 12)   # yoy values, sub-items
    fnt_t = _load_font(FONT_BOLD,    17)   # title

    # ── Build combined 7-column rows ──────────────────────────────────────
    d_rows = _section_data(dc, dp)
    m_rows = _section_data(mc, mp)
    y_rows = _section_data(yc, yp)

    combined = []
    for dr, mr, yr in zip(d_rows, m_rows, y_rows):
        if dr is None:
            combined.append(None)
        else:
            # (label, d_val, d_yoy, m_val, m_yoy, y_val, y_yoy)
            combined.append((dr[0], dr[1], dr[2], mr[1], mr[2], yr[1], yr[2]))

    # ── Measure text for column widths ────────────────────────────────────
    _tmp = Image.new("RGB", (1, 1))
    _td  = ImageDraw.Draw(_tmp)

    def _tw(text, font):
        b = _td.textbbox((0, 0), text, font=font)
        return b[2] - b[0]

    PAD = 16   # horizontal padding per cell (both sides combined)
    HDR = ["구분", "금액/수량", "전년비", "금액/수량", "전년비", "금액/수량", "전년비"]
    CFNT = [fnt_r, fnt_r, fnt_s, fnt_r, fnt_s, fnt_r, fnt_s]

    col_w = [_tw(h, fnt_b) + PAD for h in HDR]
    for row in combined:
        if row is None:
            continue
        for i, (cell, f) in enumerate(zip(row, CFNT)):
            col_w[i] = max(col_w[i], _tw(str(cell), f) + PAD)

    # Make sure period name fits its 2-column span
    for i, name in enumerate(["일별", "월누계", "연누계"]):
        needed = _tw(name, fnt_b) + PAD
        pair_w = col_w[1 + i*2] + col_w[2 + i*2]
        if needed > pair_w:
            diff = needed - pair_w
            col_w[1 + i*2] += (diff + 1) // 2
            col_w[2 + i*2] += diff // 2

    total_w = sum(col_w)
    cx = [sum(col_w[:i]) for i in range(7)]   # left-x of each column

    # ── Row heights ───────────────────────────────────────────────────────
    def _th(text, font):
        return _td.textbbox((0, 0), text, font=font)[3]

    VPAD    = 10
    base_h  = max(_th("가나Ag", fnt_r), _th("가나Ag", fnt_s))
    RH      = base_h + VPAD * 2   # data row height
    TITLE_H = 44
    SUB_H   = 28                   # 날짜+날씨 서브타이틀
    P_H     = base_h + VPAD       # period header row
    C_H     = base_h + VPAD       # column header row
    SEP_H   = 4

    n_data = sum(1 for r in combined if r is not None)
    n_sep  = sum(1 for r in combined if r is None)
    img_h  = TITLE_H + SUB_H + P_H + C_H + n_data * RH + n_sep * SEP_H + 2

    img  = Image.new("RGB", (total_w, img_h), C_ROW_ODD)
    draw = ImageDraw.Draw(img)

    # ── Drawing helpers ───────────────────────────────────────────────────
    def fill(x, y, w, h, c):
        draw.rectangle([x, y, x + w - 1, y + h - 1], fill=c)

    def cell_text(x, y, w, h, s, font, color, align="center"):
        b   = draw.textbbox((0, 0), s, font=font)
        tw_ = b[2] - b[0];  th_ = b[3] - b[1]
        ty  = y + (h - th_) // 2
        if   align == "right": tx = x + w - tw_ - PAD // 2
        elif align == "left":  tx = x + PAD // 2
        else:                  tx = x + (w - tw_) // 2
        draw.text((tx, ty), s, font=font, fill=color)

    def hline(y, color=C_BORDER):
        draw.line([(0, y), (total_w - 1, y)], fill=color)

    def vline(x, y1, y2, color=C_BORDER, width=1):
        draw.line([(x, y1), (x, y2)], fill=color, width=width)

    # ── Title ─────────────────────────────────────────────────────────────
    cur_y = 0
    fill(0, cur_y, total_w, TITLE_H, C_TITLE_BG)
    cell_text(0, cur_y, total_w, TITLE_H, "쥬쥬랜드 실적 리포트", fnt_t, C_WHITE)
    cur_y += TITLE_H

    # ── Subtitle: 날짜 + 날씨 ─────────────────────────────────────────────
    fill(0, cur_y, total_w, SUB_H, (20, 35, 50))
    wd0 = WEEKDAY_KO[today.weekday()]
    wd1 = WEEKDAY_KO[ptd.weekday()]
    w0_desc, w0_max, w0_min = weather_today
    w1_desc, w1_max, w1_min = weather_ptd
    sub0 = f"오늘 {today.strftime('%Y-%m-%d')}({wd0})  {w0_desc}  {w0_max}/{w0_min}°"
    sub1 = f"작년 {ptd.strftime('%Y-%m-%d')}({wd1})  {w1_desc}  {w1_max}/{w1_min}°"
    cell_text(0, cur_y, total_w // 2, SUB_H, sub0, fnt_s, (170, 200, 225), "center")
    cell_text(total_w // 2, cur_y, total_w // 2, SUB_H, sub1, fnt_s, (150, 175, 200), "center")
    cur_y += SUB_H
    header_top = cur_y

    # ── Period header (구분 spans P_H + C_H vertically) ───────────────────
    fill(cx[0], cur_y, col_w[0], P_H + C_H, C_PERIOD_BG)
    cell_text(cx[0], cur_y, col_w[0], P_H + C_H, "구분", fnt_b, C_WHITE)

    for i, name in enumerate(["일별", "월누계", "연누계"]):
        px = cx[1 + i * 2]
        pw = col_w[1 + i * 2] + col_w[2 + i * 2]
        fill(px, cur_y, pw, P_H, C_PERIOD_BG)
        cell_text(px, cur_y, pw, P_H, name, fnt_b, C_WHITE)

    cur_y += P_H

    # ── Column header ─────────────────────────────────────────────────────
    for i in range(1, 7):
        fill(cx[i], cur_y, col_w[i], C_H, C_COL_BG)
        cell_text(cx[i], cur_y, col_w[i], C_H, HDR[i], fnt_b, C_WHITE)

    cur_y += C_H
    header_bot = cur_y

    # Header border lines
    hline(header_top, C_BORDER)
    hline(header_bot - 1, C_BORDER)
    vline(cx[0] + col_w[0], header_top, header_bot, C_BORDER)
    vline(total_w - 1, header_top, header_bot, C_BORDER)
    # Thick dividers between period groups
    for i in (3, 5):
        vline(cx[i], header_top, header_bot, C_P_BORDER, 2)
    # Thin dividers within each period (val | yoy)
    for i in (2, 4, 6):
        vline(cx[i], header_top + P_H, header_bot, C_BORDER)

    # ── Data rows ─────────────────────────────────────────────────────────
    row_idx = 0
    for row in combined:
        if row is None:
            fill(0, cur_y, total_w, SEP_H, C_SEP_ROW)
            cur_y += SEP_H
            continue

        label    = row[0]
        is_total = "합계" in label or label == "전체매출"
        is_sub   = label.startswith("  ")
        bg = C_ROW_TOTAL if is_total else (C_ROW_ODD if row_idx % 2 == 0 else C_ROW_EVEN)
        fill(0, cur_y, total_w, RH, bg)

        lbl_font  = fnt_b if is_total else fnt_r
        lbl_color = C_SUB if is_sub else C_TEXT
        cell_text(cx[0], cur_y, col_w[0], RH, label.strip(), lbl_font, lbl_color, "left")

        for pi in range(3):
            vi, yi = 1 + pi * 2, 2 + pi * 2
            vf = fnt_b if is_total else fnt_r
            cell_text(cx[vi], cur_y, col_w[vi], RH, row[vi], vf, C_TEXT, "right")
            cell_text(cx[yi], cur_y, col_w[yi], RH, row[yi], fnt_s, _yoy_color(row[yi]), "right")

        # Row borders
        hline(cur_y + RH - 1)
        vline(cx[0] + col_w[0], cur_y, cur_y + RH, C_BORDER)
        vline(total_w - 1, cur_y, cur_y + RH, C_BORDER)
        for i in (3, 5):
            vline(cx[i], cur_y, cur_y + RH, C_P_BORDER, 2)
        for i in (2, 4, 6):
            vline(cx[i], cur_y, cur_y + RH, C_BORDER)

        cur_y  += RH
        row_idx += 1

    # Outer frame
    draw.rectangle([0, header_top, total_w - 1, cur_y - 1], outline=C_BORDER)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf


# ─── Dashboard JSON export ────────────────────────────────────────────────────

def _build_dashboard_row(label, dc, dp, mc, mp, yc, yp, *,
                         header=False, indent=False, subtotal=False, grand_total=False,
                         separator=False):
    """대시보드 HTML이 소비하는 row dict 생성."""
    if separator:
        return {"separator": True}
    return {
        "label": label,
        **({"header": True}    if header     else {}),
        **({"indent": True}    if indent     else {}),
        **({"subtotal": True}  if subtotal   else {}),
        **({"grandTotal": True} if grand_total else {}),
        "d": {"val": dc, "yoy": dp},
        "m": {"val": mc, "yoy": mp},
        "y": {"val": yc, "yoy": yp},
    }

def _fv(n, unit):
    """숫자 → "1,234원" / "1,234명" 형태."""
    return f"{fmt_num(int(n))}{unit}"

def generate_dashboard_json(today, ptd, weather_today, weather_ptd, dc, dp, mc, mp, yc, yp):
    """대시보드 index.html 이 fetch('report_data.json') 으로 읽는 JSON을 반환."""
    WEEKDAY_KO_L = ["월", "화", "수", "목", "금", "토", "일"]

    cats_dc = dc["cats"]; cats_dp = dp["cats"]
    cats_mc = mc["cats"]; cats_mp = mp["cats"]
    cats_yc = yc["cats"]; cats_yp = yp["cats"]

    # 입장
    def adm_rows():
        for period, c, p in [("d", dc, dp), ("m", mc, mp), ("y", yc, yp)]:
            pass  # calculated below

        ind = lambda c, p: (c["admission"]["individual"], p["admission"]["individual"])
        grp = lambda c, p: (c["admission"]["group"],      p["admission"]["group"])
        fre = lambda c, p: (c["admission"]["free"],        p["admission"]["free"])

        def pv(c, p): return (
            c["admission"]["individual"] + c["admission"]["group"] + c["admission"]["free"],
            p["admission"]["individual"] + p["admission"]["group"] + p["admission"]["free"],
        )

        def row3(fn, label, **kw):
            dv, dpv = fn(dc, dp); mv, mpv = fn(mc, mp); yv, ypv = fn(yc, yp)
            return _build_dashboard_row(
                label,
                _fv(dv,"명"), fyoy(yoy(dv,dpv)),
                _fv(mv,"명"), fyoy(yoy(mv,mpv)),
                _fv(yv,"명"), fyoy(yoy(yv,ypv)),
                **kw,
            )

        return [
            row3(pv,  "입장(전체)", header=True),
            row3(ind, "개인",       indent=True),
            row3(grp, "단체",       indent=True),
            row3(fre, "무료",       indent=True),
        ]

    # 먹이
    def food_row():
        dv=dc["food"]["amt"]; dpv=dp["food"]["amt"]
        mv=mc["food"]["amt"]; mpv=mp["food"]["amt"]
        yv=yc["food"]["amt"]; ypv=yp["food"]["amt"]
        return _build_dashboard_row(
            "먹이판매",
            _fv(dv,"원"), fyoy(yoy(dv,dpv)),
            _fv(mv,"원"), fyoy(yoy(mv,mpv)),
            _fv(yv,"원"), fyoy(yoy(yv,ypv)),
        )

    # 점포
    def store_rows_and_subtotal():
        rows = []
        tc = tp = tm_c = tm_p = ty_c = ty_p = 0
        for k, lbl in STORE_KEYS:
            dv  = cats_dc.get(k,{}).get("amt",0); dpv = cats_dp.get(k,{}).get("amt",0)
            mv  = cats_mc.get(k,{}).get("amt",0); mpv = cats_mp.get(k,{}).get("amt",0)
            yv  = cats_yc.get(k,{}).get("amt",0); ypv = cats_yp.get(k,{}).get("amt",0)
            tc += dv; tp += dpv; tm_c += mv; tm_p += mpv; ty_c += yv; ty_p += ypv
            rows.append(_build_dashboard_row(
                lbl,
                _fv(dv,"원"), fyoy(yoy(dv,dpv)),
                _fv(mv,"원"), fyoy(yoy(mv,mpv)),
                _fv(yv,"원"), fyoy(yoy(yv,ypv)),
            ))
        rows.append(_build_dashboard_row(
            "점포합계",
            _fv(tc,"원"), fyoy(yoy(tc,tp)),
            _fv(tm_c,"원"), fyoy(yoy(tm_c,tm_p)),
            _fv(ty_c,"원"), fyoy(yoy(ty_c,ty_p)),
            subtotal=True,
        ))
        return rows

    # 전체매출 (온라인티켓 ₩0이므로 OKPOS 실집계만 포함)
    all_dc=sum(v["amt"] for v in cats_dc.values()); all_dp=sum(v["amt"] for v in cats_dp.values())
    all_mc=sum(v["amt"] for v in cats_mc.values()); all_mp=sum(v["amt"] for v in cats_mp.values())
    all_yc=sum(v["amt"] for v in cats_yc.values()); all_yp=sum(v["amt"] for v in cats_yp.values())
    total_row = _build_dashboard_row(
        "전체매출",
        _fv(all_dc,"원"), fyoy(yoy(all_dc,all_dp)),
        _fv(all_mc,"원"), fyoy(yoy(all_mc,all_mp)),
        _fv(all_yc,"원"), fyoy(yoy(all_yc,all_yp)),
        grand_total=True,
    )

    # 온라인 외부정산 수량 (참고용)
    naver_d = dc["online"]["naver"]; ls_d = dc["online"]["ls"]
    naver_m = mc["online"]["naver"]; ls_m = mc["online"]["ls"]
    naver_y = yc["online"]["naver"]; ls_y = yc["online"]["ls"]

    return {
        "today_date": f"{today.strftime('%Y-%m-%d')} ({WEEKDAY_KO[today.weekday()]})",
        "prev_date":  f"{ptd.strftime('%Y-%m-%d')} ({WEEKDAY_KO[ptd.weekday()]})",
        "today_weather": {"desc": weather_today[0], "tmax": weather_today[1], "tmin": weather_today[2]},
        "prev_weather":  {"desc": weather_ptd[0],   "tmax": weather_ptd[1],   "tmin": weather_ptd[2]},
        "kpi": {
            "daily_sales":         f"{fmt_num(all_dc)}",
            "daily_visitors":      f"{fmt_num(dc['admission']['individual'] + dc['admission']['group'] + dc['admission']['free'])}",
            "ytd_sales":           f"{fmt_num(all_yc)}",
            "daily_sales_yoy":     fyoy(yoy(all_dc, all_dp)),
            "daily_visitors_yoy":  fyoy(yoy(
                dc["admission"]["individual"] + dc["admission"]["group"] + dc["admission"]["free"],
                dp["admission"]["individual"] + dp["admission"]["group"] + dp["admission"]["free"],
            )),
            "ytd_sales_yoy":       fyoy(yoy(all_yc, all_yp)),
        },
        # 온라인 외부정산: OKPOS 매출 ₩0, 실수익은 네이버/LS 플랫폼에서 별도 정산
        "online_external": {
            "naver": {"daily": naver_d, "monthly": naver_m, "ytd": naver_y},
            "ls":    {"daily": ls_d,    "monthly": ls_m,    "ytd": ls_y},
        },
        "rows": [
            *adm_rows(),
            {"separator": True},
            food_row(),
            {"separator": True},
            *store_rows_and_subtotal(),
            total_row,
        ],
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M KST"),
    }


# ─── Entry point ──────────────────────────────────────────────────────────────

async def main():
    today = datetime.now(KST).date()
    ms  = today.replace(day=1)
    pms = ms.replace(year=ms.year - 1)
    ys  = today.replace(month=1, day=1)
    pys = ys.replace(year=ys.year - 1)
    ptd = nearest_same_weekday_last_year(today)  # 전년 가장 가까운 동일 요일
    fmt_d = lambda d: d.strftime("%Y-%m-%d")

    sess = do_login()

    print("=== Current year ===")
    tn, tv = get_api_token(sess)
    dc = fetch_sales(sess, tn, tv, fmt_d(today), fmt_d(today))
    tn, tv = get_api_token(sess)
    mc = fetch_sales(sess, tn, tv, fmt_d(ms), fmt_d(today))
    yc = fetch_sales_chunked(sess, fmt_d(ys), fmt_d(today))

    print("=== Previous year ===")
    tn, tv = get_api_token(sess)
    dp = fetch_sales(sess, tn, tv, fmt_d(ptd), fmt_d(ptd))
    tn, tv = get_api_token(sess)
    mp = fetch_sales(sess, tn, tv, fmt_d(pms), fmt_d(ptd))
    yp = fetch_sales_chunked(sess, fmt_d(pys), fmt_d(ptd))

    print("Fetching weather...")
    weather_today = get_weather(today)
    weather_ptd   = get_weather(ptd)
    print(f"  today: {weather_today}, ptd({ptd}): {weather_ptd}")

    # 대시보드 JSON 저장 (dashboard/report_data.json)
    print("Generating dashboard JSON...")
    dash_json = generate_dashboard_json(today, ptd, weather_today, weather_ptd, dc, dp, mc, mp, yc, yp)
    json_path = os.path.join(os.path.dirname(__file__), "dashboard", "report_data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(dash_json, f, ensure_ascii=False, indent=2)
    print(f"  Saved: {json_path}")

    print("Creating image...")
    img_buf = create_report_image(today, ptd, weather_today, weather_ptd, dc, dp, mc, mp, yc, yp)

    bot = telegram.Bot(token=BOT_TOKEN)
    await bot.send_photo(chat_id=CHAT_ID, photo=img_buf)
    print("Sent!")


if __name__ == "__main__":
    asyncio.run(main())
