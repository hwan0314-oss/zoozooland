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

BASE_URL      = "https://kis.okpos.co.kr"
API_URL       = BASE_URL + "/sale/sale/ddd.htmlSheetAction"
API_SHOP_URL  = BASE_URL + "/sale/shopsale/ddd.htmlSheetAction"

USER_ID   = os.environ["KIS_ID"]
USER_PW   = os.environ["KIS_PW"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID   = -1003990713280

KST = timezone(timedelta(hours=9))
KMA_API_KEY = os.environ.get("KMA_API_KEY", "")

# 외부 플랫폼(네이버 스마트플레이스 / LS파트너) 결제 상품:
#   - OKPOS에는 qty만 기록, TOT_SALE_AMT = 0 (대사 목적 0원 상품)
#   - 실제 정산금액은 각 플랫폼에서 별도 집계
NAVER_TICKETS  = {"네이버 주중", "네이버 주말"}
LS_TICKETS     = {"온라인티켓(LS)"}
ONLINE_TICKETS = NAVER_TICKETS | LS_TICKETS  # OKPOS amt=0 → online_ticket_price() 로 추정매출 반영
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

# OKPOS 매장별매출분석 API (dayranking010) SHOP_NM 기준 점포 목록
# "매표소"와 "먹이판매"는 동일 매표소 부스의 별도 POS 단말 → fetch_shop_sales에서 "매표소"로 통합
STORE_KEYS = [
    ("매표소",       "매표소"),
    ("쥬쥬레스토랑", "쥬쥬레스토랑"),
    ("공방카페",     "공방카페"),
    ("파충류관",     "파충류관"),
    ("열린매대",     "열린매대"),
    ("팝업스토어",   "팝업스토어"),
    ("무인매장",     "무인매장"),
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


def get_shop_token(sess):
    r = sess.get(
        BASE_URL + "/sale/shopsale/dayranking010.jsp",
        headers={"Referer": BASE_URL + "/login/top_frame.jsp"}, verify=False, timeout=30,
    )
    n, v = extract_token(r.text)
    if not n:
        raise RuntimeError(f"No token in dayranking010.jsp. HTML: {r.text[:200]}")
    return n, v


def fetch_shop_sales(sess, date_from, date_to):
    """매장별매출분석 API → {SHOP_NM: {"amt": DCM_SALE_AMT, "cnt": TOT_SALE_CNT}}"""
    n, v = get_shop_token(sess)
    payload = {
        n: v,
        "S_CONTROLLER": "sale.shopsale.dayranking010",
        "S_METHOD": "search",
        "SHEETSEQ": "1", "S_SAVENAME": "", "S_ORDERBY": "",
        "date1_1": date_from, "date1_2": date_to,
        "date_period1": "366",
        "ss_SHOP_TYPE_FG": "", "ss_SHOP_GROUP_CD": "",
        "ss_TYPE_UD": "U", "ss_SEL_CNT": "500",
        "EX_CST": "false",
    }
    r = sess.post(
        API_SHOP_URL, data=payload,
        headers={"Referer": BASE_URL + "/sale/shopsale/dayranking010.jsp"},
        verify=False, timeout=60,
    )
    print(f"Shop API [{date_from}~{date_to}]: {r.status_code} len={len(r.text)}")
    data = r.json()
    if "Result" in data and data["Result"].get("Code", 0) < 0:
        raise RuntimeError(f"Shop API error: {data['Result']['Message']}")
    shops = {}
    for row in data.get("Data", []):
        nm = row.get("SHOP_NM", "")
        if nm == "먹이판매":
            # 매표소 부스에서 별도 POS 단말로 운영 중인 매장명 → "매표소"로 통합
            nm = "매표소"
        amt = int(row.get("DCM_SALE_AMT") or 0)
        cnt = int(row.get("TOT_SALE_CNT") or 0)
        if nm in shops:
            shops[nm]["amt"] += amt
            shops[nm]["cnt"] += cnt
        else:
            shops[nm] = {"amt": amt, "cnt": cnt}
    print(f"  Shops: {[(k, v['amt']) for k, v in shops.items()]}")
    return shops


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

    cats          = {}
    food          = {"qty": 0, "amt": 0}
    admission     = {"individual": 0, "group": 0, "free": 0}
    admission_rev = {"individual_pos": 0, "group": 0}
    online_rev    = {"naver": 0, "ls": 0}  # 네이버/LS 추정매출(전체매출 합산용)

    for row in rows:
        cat     = row.get("MCLS_NM") or row.get("LCLS_NM") or "기타"
        prod_nm = (row.get("PROD_NM") or "").strip()
        scls_nm = (row.get("SCLS_NM") or "").strip()
        qty     = int(row.get("SALE_QTY", 0) or 0)
        amt     = int(row.get("DCM_SALE_AMT", 0) or 0)  # 할인 후 실결제액

        if cat not in cats:
            cats[cat] = {"qty": 0, "amt": 0}
        cats[cat]["qty"] += qty
        cats[cat]["amt"] += amt

        # 먹이매출: 메뉴 > 동물먹이 > 동물먹이
        if cat == "동물먹이":
            food["qty"] += qty
            food["amt"] += amt

        # 입장객/입장매출: 메뉴 > 매표소 > 개인 / 단체 (SCLS_NM 기준)
        if cat == "매표소":
            if scls_nm == "단체":
                admission["group"] += qty
                admission_rev["group"] += amt
            elif scls_nm == "개인":
                if prod_nm in FREE_PRODUCTS:
                    # 무료 입장 (24개월미만, 초대권)
                    admission["free"] += qty
                else:
                    admission["individual"] += qty
                    if prod_nm in ONLINE_TICKETS:
                        # 네이버/LS 온라인 티켓: OKPOS amt=0 → 기간별 단가로 추정 매출 반영
                        sale_d = row.get("SALE_DATE", "")
                        rev    = qty * online_ticket_price(sale_d)
                        admission_rev["individual_pos"] += rev
                        if prod_nm in NAVER_TICKETS:
                            online_rev["naver"] += rev
                        else:
                            online_rev["ls"] += rev
                    else:
                        admission_rev["individual_pos"] += amt
            # else: 매표소 내 비입장 상품(화분·제로콜라 등) → 집계 제외

    print(f"  Categories: {list(cats.keys())}")
    print(f"  Admission rev: pos_ind={admission_rev['individual_pos']:,}, grp={admission_rev['group']:,}")
    print(f"  Online rev est: naver={online_rev['naver']:,}, ls={online_rev['ls']:,}")
    return {
        "cats": cats, "food": food,
        "admission": admission, "admission_rev": admission_rev, "online_rev": online_rev,
    }


def fetch_sales_chunked(sess, date_from_str, date_to_str, max_days=90):
    start = date.fromisoformat(date_from_str)
    end   = date.fromisoformat(date_to_str)
    total = {
        "cats": {},
        "food": {"qty": 0, "amt": 0},
        "admission": {"individual": 0, "group": 0, "free": 0},
        "admission_rev": {"individual_pos": 0, "group": 0},
        "online_rev": {"naver": 0, "ls": 0},
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
        for k in ("individual_pos", "group"):
            total["admission_rev"][k] += chunk["admission_rev"][k]
        for k in ("naver", "ls"):
            total["online_rev"][k] += chunk["online_rev"][k]
        current = chunk_end + timedelta(days=1)
    return total


# ─── Data helpers ─────────────────────────────────────────────────────────────

def online_ticket_price(sale_date_str):
    """네이버/LS 온라인 티켓 건당 입장료 (기간별 단가)."""
    try:
        s = str(sale_date_str).replace("-", "")
        d = date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    except Exception:
        return 15_000
    if date(2025, 1, 1) <= d <= date(2025, 2, 28):
        return 12_000
    if date(2026, 3, 4) <= d <= date(2026, 3, 31):
        return 10_000
    return 15_000


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
    shops_c = curr.get("shops", {})
    shops_p = prev.get("shops", {})
    fa      = curr["food"]["amt"]
    pfa     = prev["food"]["amt"]
    adm_c   = curr["admission"]; adm_p = prev["admission"]
    rev_c   = curr["admission_rev"]; rev_p = prev["admission_rev"]
    onl_c   = curr["online_rev"]; onl_p = prev["online_rev"]

    # 입장객 수 (명)
    ind_c = adm_c["individual"]; ind_p = adm_p["individual"]
    grp_c = adm_c["group"];      grp_p = adm_p["group"]
    fre_c = adm_c["free"];       fre_p = adm_p["free"]
    tot_c = ind_c + grp_c + fre_c
    tot_p = ind_p + grp_p + fre_p

    # 입장매출 (원): 개인(POS+온라인추정) + 단체
    ir_c = rev_c["individual_pos"]; ir_p = rev_p["individual_pos"]
    gr_c = rev_c["group"];          gr_p = rev_p["group"]
    tr_c = ir_c + gr_c;             tr_p = ir_p + gr_p

    # 점포별
    store_rows = []
    for k, lbl in STORE_KEYS:
        ca = shops_c.get(k, {}).get("amt", 0)
        pa = shops_p.get(k, {}).get("amt", 0)
        store_rows.append((f"  {lbl}", f"{fmt_num(ca)}원", fyoy(yoy(ca, pa))))

    # 전체매출: 점포별 매출 합계 + 네이버/LS 온라인 추정매출
    shop_c = sum(v["amt"] for v in shops_c.values())
    shop_p = sum(v["amt"] for v in shops_p.values())
    all_c  = shop_c + onl_c["naver"] + onl_c["ls"]
    all_p  = shop_p + onl_p["naver"] + onl_p["ls"]

    return [
        # ── 입장객 수 ──
        ("입장(전체)", f"{fmt_num(tot_c)}명", fyoy(yoy(tot_c, tot_p))),
        ("  개인",     f"{fmt_num(ind_c)}명", fyoy(yoy(ind_c, ind_p))),
        ("  단체",     f"{fmt_num(grp_c)}명", fyoy(yoy(grp_c, grp_p))),
        ("  무료",     f"{fmt_num(fre_c)}명", fyoy(yoy(fre_c, fre_p))),
        None,
        # ── 입장매출 (개인 POS+온라인추정 + 단체) ──
        ("입장매출",     f"{fmt_num(tr_c)}원", fyoy(yoy(tr_c, tr_p))),
        ("  개인(POS)",  f"{fmt_num(ir_c)}원", fyoy(yoy(ir_c, ir_p))),
        ("  단체",       f"{fmt_num(gr_c)}원", fyoy(yoy(gr_c, gr_p))),
        None,
        # ── 먹이매출 ──
        ("먹이매출",   f"{fmt_num(fa)}원", fyoy(yoy(fa, pfa))),
        None,
        # ── 점포별 ──
        *store_rows,
        None,
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
    # ── Colors (Tailwind equivalents) ──────────────────────────────────────
    CS900    = (15, 23, 42)
    CS800    = (30, 41, 59)
    CS700    = (51, 65, 85)
    CWHITE   = (255, 255, 255)
    CGR50    = (249, 250, 251)
    CGR100   = (243, 244, 246)
    CGR200   = (229, 231, 235)
    CGR400   = (156, 163, 175)
    CGR500   = (107, 114, 128)
    CGR700   = (55, 65, 81)
    CINDIG   = (79, 70, 229)
    CINDIG1  = (224, 231, 255)
    CINDIG50 = (238, 242, 255)
    CBLUE50  = (239, 246, 255)
    CBLUE100 = (219, 234, 254)
    CBLUE700 = (29, 78, 216)
    CVIOL50  = (245, 243, 255)
    CVIOL100 = (237, 233, 254)
    CVIOL700 = (109, 40, 217)
    CEMLD    = (5, 150, 105)
    CEMLD_BG = (209, 250, 229)
    CROSE    = (225, 29, 72)
    CROSE_BG = (255, 228, 230)

    # ── Fonts ──────────────────────────────────────────────────────────────
    fnt_hd = _load_font(FONT_BOLD,    20)
    fnt_hs = _load_font(FONT_REGULAR, 11)
    fnt_kv = _load_font(FONT_BOLD,    21)
    fnt_kl = _load_font(FONT_REGULAR, 10)
    fnt_dv = _load_font(FONT_BOLD,    13)
    fnt_ds = _load_font(FONT_REGULAR, 11)
    fnt_th = _load_font(FONT_BOLD,    13)
    fnt_ch = _load_font(FONT_BOLD,    11)
    fnt_br = _load_font(FONT_BOLD,    13)
    fnt_nr = _load_font(FONT_REGULAR, 13)
    fnt_y  = _load_font(FONT_BOLD,    10)
    fnt_ft = _load_font(FONT_REGULAR, 10)

    # ── Layout ─────────────────────────────────────────────────────────────
    TOTAL_W  = 920
    LPAD     = 20            # left/right margin for table
    TABLE_W  = TOTAL_W - LPAD * 2   # 880
    HDR_H    = 72
    INFO_H   = 160
    SECHDR_H = 38
    PHDR_H   = 30
    CHDR_H   = 26
    ROW_H    = 32
    SEP_H    = 6
    FOOT_H   = 82

    # col widths sum = TABLE_W = 880
    col_w = [165, 143, 97, 143, 97, 143, 92]
    cx = [LPAD + sum(col_w[:i]) for i in range(7)]

    # ── Build combined rows ─────────────────────────────────────────────────
    d_rows = _section_data(dc, dp)
    m_rows = _section_data(mc, mp)
    y_rows = _section_data(yc, yp)

    combined = []
    for dr, mr, yr in zip(d_rows, m_rows, y_rows):
        if dr is None:
            combined.append(None)
        else:
            combined.append((dr[0], dr[1], dr[2], mr[1], mr[2], yr[1], yr[2]))

    n_data = sum(1 for r in combined if r is not None)
    n_sep  = sum(1 for r in combined if r is None)
    total_h = HDR_H + INFO_H + SECHDR_H + PHDR_H + CHDR_H + n_data * ROW_H + n_sep * SEP_H + FOOT_H

    img  = Image.new("RGB", (TOTAL_W, total_h), CWHITE)
    draw = ImageDraw.Draw(img)

    # ── Helpers ─────────────────────────────────────────────────────────────
    def rrect(x, y, w, h, r, fill_c, outline_c=None, ow=1):
        try:
            kw = {"radius": r, "fill": fill_c}
            if outline_c:
                kw["outline"] = outline_c
                kw["width"] = ow
            draw.rounded_rectangle([x, y, x + w - 1, y + h - 1], **kw)
        except (AttributeError, TypeError):
            draw.rectangle([x, y, x + w - 1, y + h - 1], fill=fill_c)

    def _bb(text, font):
        return draw.textbbox((0, 0), text, font=font)

    def tc(text, font, fill, rx, ry, rw, rh):
        b = _bb(text, font)
        tw, th = b[2] - b[0], b[3] - b[1]
        draw.text((rx + (rw - tw) // 2, ry + (rh - th) // 2 - b[1]), text, font=font, fill=fill)

    def tl(text, font, fill, rx, ry, rw, rh, hpad=10):
        b = _bb(text, font)
        th = b[3] - b[1]
        draw.text((rx + hpad, ry + (rh - th) // 2 - b[1]), text, font=font, fill=fill)

    def tr(text, font, fill, rx, ry, rw, rh, hpad=10):
        b = _bb(text, font)
        tw, th = b[2] - b[0], b[3] - b[1]
        draw.text((rx + rw - tw - hpad, ry + (rh - th) // 2 - b[1]), text, font=font, fill=fill)

    def badge(yoy_str, bx, by, bw, bh):
        if yoy_str == "N/A":
            bg, fg, sym = CGR100, CGR500, "N/A"
        elif yoy_str.startswith("+"):
            bg, fg, sym = CEMLD_BG, CEMLD, "▲ " + yoy_str[1:]
        elif yoy_str.startswith("-"):
            bg, fg, sym = CROSE_BG, CROSE, "▼ " + yoy_str[1:]
        else:
            bg, fg, sym = CGR100, CGR500, yoy_str
        b = _bb(sym, fnt_y)
        tw, th = b[2] - b[0], b[3] - b[1]
        bw2, bh2 = tw + 14, th + 8
        bx2 = bx + (bw - bw2) // 2
        by2 = by + (bh - bh2) // 2
        rrect(bx2, by2, bw2, bh2, 4, bg)
        draw.text((bx2 + 7, by2 + 4 - b[1]), sym, font=fnt_y, fill=fg)

    cur_y = 0

    # ═══ HEADER ════════════════════════════════════════════════════════════
    draw.rectangle([0, 0, TOTAL_W - 1, HDR_H - 1], fill=CS900)
    LOGO = 44
    lx, ly = 16, (HDR_H - LOGO) // 2
    rrect(lx, ly, LOGO, LOGO, 8, CINDIG)
    tc("ZZ", fnt_dv, CWHITE, lx, ly, LOGO, LOGO)
    TX = lx + LOGO + 12
    draw.text((TX, ly + 2), "쥬쥬랜드 실적 리포트", font=fnt_hd, fill=CWHITE)
    b = _bb("쥬쥬랜드 실적 리포트", fnt_hd)
    draw.text((TX, ly + 2 + (b[3] - b[1]) + 5), "임원진 보고용 대시보드", font=fnt_hs, fill=CGR400)
    cur_y = HDR_H

    # ═══ INFO ROW ══════════════════════════════════════════════════════════
    draw.rectangle([0, cur_y, TOTAL_W - 1, cur_y + INFO_H - 1], fill=CGR50)
    draw.line([(0, cur_y + INFO_H - 1), (TOTAL_W - 1, cur_y + INFO_H - 1)], fill=CGR200)

    IP   = 10
    LW   = 280
    CH   = (INFO_H - IP * 3) // 2

    def date_card(dx, dy, dw, dh, d_obj, wdesc, wmax, wmin, pfx):
        rrect(dx, dy, dw, dh, 8, CWHITE, CGR200)
        wd = WEEKDAY_KO[d_obj.weekday()]
        draw.text((dx + 10, dy + 7), pfx, font=fnt_kl, fill=CGR500)
        draw.text((dx + 10, dy + 21), f"{d_obj.strftime('%Y.%m.%d')} ({wd})", font=fnt_dv, fill=CGR700)
        wstr = f"{wdesc}  {wmax}° / {wmin}°" if wdesc else f"{wmax}° / {wmin}°"
        draw.text((dx + 10, dy + dh - 22), wstr, font=fnt_ds, fill=CGR500)

    w0_desc, w0_max, w0_min = weather_today
    w1_desc, w1_max, w1_min = weather_ptd
    date_card(IP, cur_y + IP, LW - IP * 2, CH, today, w0_desc, w0_max, w0_min, "오늘")
    date_card(IP, cur_y + IP * 2 + CH, LW - IP * 2, CH, ptd, w1_desc, w1_max, w1_min, "작년")

    # KPI cards
    shops_dc = dc.get("shops", {})
    shops_dp = dp.get("shops", {})
    shops_yc = yc.get("shops", {})
    shops_yp = yp.get("shops", {})
    adm_dc   = dc.get("admission", {})
    adm_dp   = dp.get("admission", {})

    d_amt_c = sum(v["amt"] for v in shops_dc.values()) + dc["online_rev"]["naver"] + dc["online_rev"]["ls"]
    d_amt_p = sum(v["amt"] for v in shops_dp.values()) + dp["online_rev"]["naver"] + dp["online_rev"]["ls"]
    y_amt_c = sum(v["amt"] for v in shops_yc.values()) + yc["online_rev"]["naver"] + yc["online_rev"]["ls"]
    y_amt_p = sum(v["amt"] for v in shops_yp.values()) + yp["online_rev"]["naver"] + yp["online_rev"]["ls"]
    d_vis_c = adm_dc.get("individual", 0) + adm_dc.get("group", 0)
    d_vis_p = adm_dp.get("individual", 0) + adm_dp.get("group", 0)

    kpis = [
        ("일일 전체매출",   f"₩{fmt_num(d_amt_c)}", yoy(d_amt_c, d_amt_p)),
        ("일일 유료 입장객", f"{fmt_num(d_vis_c)}명", yoy(d_vis_c, d_vis_p)),
        ("연누계 전체매출", f"₩{fmt_num(y_amt_c)}", yoy(y_amt_c, y_amt_p)),
    ]

    RX   = LW
    RW   = TOTAL_W - LW
    KW   = (RW - IP * 4) // 3
    KH   = INFO_H - IP * 2

    for i, (klbl, kval, kyoy) in enumerate(kpis):
        kx = RX + IP + i * (KW + IP)
        ky = cur_y + IP
        rrect(kx, ky, KW, KH, 8, CWHITE, CGR200)
        draw.text((kx + 12, ky + 12), klbl, font=fnt_kl, fill=CGR500)
        draw.text((kx + 12, ky + 30), kval, font=fnt_kv, fill=CS900)
        ystr = fyoy(kyoy)
        if ystr != "N/A":
            if ystr.startswith("+"):
                bg, fg, sym = CEMLD_BG, CEMLD, "▲ " + ystr[1:]
            else:
                bg, fg, sym = CROSE_BG, CROSE, "▼ " + ystr[1:]
            b = _bb(sym, fnt_y)
            bw2 = b[2] - b[0] + 14;  bh2 = b[3] - b[1] + 8
            rrect(kx + 12, ky + KH - bh2 - 12, bw2, bh2, 4, bg)
            draw.text((kx + 12 + 7, ky + KH - bh2 - 12 + 4 - b[1]), sym, font=fnt_y, fill=fg)

    cur_y += INFO_H

    # ═══ TABLE SECTION HEADER ══════════════════════════════════════════════
    draw.rectangle([0, cur_y, TOTAL_W - 1, cur_y + SECHDR_H - 1], fill=CS800)
    tl("상세 실적 현황표", fnt_th, CWHITE, 0, cur_y, 300, SECHDR_H, hpad=LPAD)

    # Legend
    for sym, bg, fg, lx2 in [("▲", CEMLD_BG, CEMLD, TOTAL_W - 250), ("▼", CROSE_BG, CROSE, TOTAL_W - 145)]:
        b = _bb(sym, fnt_y)
        bh2 = b[3] - b[1] + 8;  bw2 = b[2] - b[0] + 12
        by2 = cur_y + (SECHDR_H - bh2) // 2
        rrect(lx2, by2, bw2, bh2, 3, bg)
        draw.text((lx2 + 6, by2 + 4 - b[1]), sym, font=fnt_y, fill=fg)
        lbl = "전년대비증가" if sym == "▲" else "전년대비감소"
        b2 = _bb(lbl, fnt_hs)
        draw.text((lx2 + bw2 + 4, cur_y + (SECHDR_H - (b2[3] - b2[1])) // 2 - b2[1]), lbl, font=fnt_hs, fill=CGR400)

    cur_y += SECHDR_H

    # ═══ COLUMN HEADERS ════════════════════════════════════════════════════
    tbl_top = cur_y
    draw.rectangle([LPAD, cur_y, LPAD + TABLE_W - 1, cur_y + PHDR_H + CHDR_H - 1], fill=CGR50)

    # 구분 col
    draw.rectangle([cx[0], cur_y, cx[0] + col_w[0] - 1, cur_y + PHDR_H + CHDR_H - 1], fill=CS700)
    tc("구분", fnt_ch, CWHITE, cx[0], cur_y, col_w[0], PHDR_H + CHDR_H)

    period_cfg = [
        (1, "일별",   CBLUE100, CBLUE700, CBLUE50),
        (3, "월누계", CINDIG1,  CINDIG,   CINDIG50),
        (5, "연누계", CVIOL100, CVIOL700, CVIOL50),
    ]
    for ci, name, hbg, hfg, sbg in period_cfg:
        pw = col_w[ci] + col_w[ci + 1]
        draw.rectangle([cx[ci], cur_y, cx[ci] + pw - 1, cur_y + PHDR_H - 1], fill=hbg)
        tc(name, fnt_ch, hfg, cx[ci], cur_y, pw, PHDR_H)
        draw.rectangle([cx[ci],     cur_y + PHDR_H, cx[ci] + col_w[ci] - 1,     cur_y + PHDR_H + CHDR_H - 1], fill=sbg)
        draw.rectangle([cx[ci + 1], cur_y + PHDR_H, cx[ci + 1] + col_w[ci+1] - 1, cur_y + PHDR_H + CHDR_H - 1], fill=sbg)
        tc("금액/수량", fnt_ch, hfg, cx[ci],     cur_y + PHDR_H, col_w[ci],     CHDR_H)
        tc("전년비",    fnt_ch, hfg, cx[ci + 1], cur_y + PHDR_H, col_w[ci + 1], CHDR_H)

    # Header grid lines
    draw.rectangle([LPAD, cur_y, LPAD + TABLE_W - 1, cur_y + PHDR_H + CHDR_H - 1], outline=CGR200)
    for ci in (1, 3, 5):
        draw.line([(cx[ci], cur_y), (cx[ci], cur_y + PHDR_H + CHDR_H - 1)], fill=CGR200)
    for ci in (2, 4, 6):
        draw.line([(cx[ci], cur_y + PHDR_H), (cx[ci], cur_y + PHDR_H + CHDR_H - 1)], fill=CGR200)
    draw.line([(cx[1], cur_y + PHDR_H), (LPAD + TABLE_W - 1, cur_y + PHDR_H)], fill=CGR200)

    cur_y += PHDR_H + CHDR_H

    # ═══ DATA ROWS ══════════════════════════════════════════════════════════
    for row in combined:
        if row is None:
            draw.rectangle([LPAD, cur_y, LPAD + TABLE_W - 1, cur_y + SEP_H - 1], fill=CGR100)
            cur_y += SEP_H
            continue

        label = row[0]
        is_grand  = label.strip() == "전체매출"
        is_sub_tt = "합계" in label
        is_sub    = label.startswith("  ")

        if is_grand:
            row_bg = CS800;   val_fg = CWHITE;  lbl_fg = CWHITE;   lbl_f = fnt_br
        elif is_sub_tt:
            row_bg = CINDIG50; val_fg = CS700;   lbl_fg = CINDIG;   lbl_f = fnt_br
        else:
            row_bg = CWHITE;  val_fg = CGR700;  lbl_fg = CGR500 if is_sub else CGR700;  lbl_f = fnt_nr

        draw.rectangle([LPAD, cur_y, LPAD + TABLE_W - 1, cur_y + ROW_H - 1], fill=row_bg)

        # Label
        lbl_text = label.strip()
        if is_sub:
            dot_x = cx[0] + 18
            b = _bb("·", fnt_nr)
            draw.text((dot_x, cur_y + (ROW_H - (b[3] - b[1])) // 2 - b[1]), "·", font=fnt_nr, fill=CGR400)
            tl(lbl_text, lbl_f, lbl_fg, dot_x + (b[2] - b[0]) + 4, cur_y, col_w[0] - 30, ROW_H, hpad=0)
        else:
            tl(lbl_text, lbl_f, lbl_fg, cx[0], cur_y, col_w[0], ROW_H, hpad=12)

        # Values + YoY badges
        for pi in range(3):
            vi, yi = 1 + pi * 2, 2 + pi * 2
            vf = fnt_br if (is_grand or is_sub_tt) else fnt_nr
            tr(row[vi], vf, val_fg, cx[vi], cur_y, col_w[vi], ROW_H)
            if is_grand:
                tc(row[yi], fnt_y, CWHITE, cx[yi], cur_y, col_w[yi], ROW_H)
            else:
                badge(row[yi], cx[yi], cur_y, col_w[yi], ROW_H)

        # Row borders
        draw.line([(LPAD, cur_y + ROW_H - 1), (LPAD + TABLE_W - 1, cur_y + ROW_H - 1)], fill=CGR200)
        for ci in (1, 2, 3, 4, 5, 6):
            draw.line([(cx[ci], cur_y), (cx[ci], cur_y + ROW_H - 1)], fill=CGR200)

        cur_y += ROW_H

    # Table outer border
    draw.rectangle([LPAD, tbl_top, LPAD + TABLE_W - 1, cur_y - 1], outline=CGR200)

    # ═══ FOOTER ════════════════════════════════════════════════════════════
    draw.rectangle([0, cur_y, TOTAL_W - 1, cur_y + FOOT_H - 1], fill=CGR100)
    draw.line([(0, cur_y), (TOTAL_W - 1, cur_y)], fill=CGR200)
    foot_notes = [
        "※ 모든 금액은 부가세(VAT 10%) 포함 금액입니다.",
        "※ 네이버·LS 매출은 OKPOS 수량 × 기간별 단가(기본 ₩15,000 / 2025.01~02 ₩12,000 / 2026.03 ₩10,000) 추정값입니다.",
        "※ 일별 실적은 전년의 같은 요일(최근접 날짜)과 비교됩니다.",
        "※ 먹이매출은 매표소·먹이판매 각 포스에서 먹이 상품 매출만 별도 합산한 금액입니다.",
    ]
    fn_y = cur_y + 8
    for fn in foot_notes:
        b = _bb(fn, fnt_ft)
        draw.text((LPAD, fn_y - b[1]), fn, font=fnt_ft, fill=CGR500)
        fn_y += (b[3] - b[1]) + 4

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

    shops_dc = dc.get("shops", {}); shops_dp = dp.get("shops", {})
    shops_mc = mc.get("shops", {}); shops_mp = mp.get("shops", {})
    shops_yc = yc.get("shops", {}); shops_yp = yp.get("shops", {})

    # 입장객 수
    def adm_rows():
        def pv(c, p): return (
            c["admission"]["individual"] + c["admission"]["group"] + c["admission"]["free"],
            p["admission"]["individual"] + p["admission"]["group"] + p["admission"]["free"],
        )
        ind = lambda c, p: (c["admission"]["individual"], p["admission"]["individual"])
        grp = lambda c, p: (c["admission"]["group"],      p["admission"]["group"])
        fre = lambda c, p: (c["admission"]["free"],        p["admission"]["free"])

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

    # 입장매출 (POS 개인 + 단체; 온라인은 외부정산으로 추후 추가)
    def adm_rev_rows():
        def rev3(fn, label, **kw):
            dv, dpv = fn(dc, dp); mv, mpv = fn(mc, mp); yv, ypv = fn(yc, yp)
            return _build_dashboard_row(
                label,
                _fv(dv,"원"), fyoy(yoy(dv,dpv)),
                _fv(mv,"원"), fyoy(yoy(mv,mpv)),
                _fv(yv,"원"), fyoy(yoy(yv,ypv)),
                **kw,
            )
        tot = lambda c, p: (
            c["admission_rev"]["individual_pos"] + c["admission_rev"]["group"],
            p["admission_rev"]["individual_pos"] + p["admission_rev"]["group"],
        )
        ind = lambda c, p: (c["admission_rev"]["individual_pos"], p["admission_rev"]["individual_pos"])
        grp = lambda c, p: (c["admission_rev"]["group"], p["admission_rev"]["group"])
        return [
            rev3(tot, "입장매출",    header=True),
            rev3(ind, "  개인(POS)", indent=True),
            rev3(grp, "  단체",      indent=True),
        ]

    # 먹이매출 (메뉴 > 동물먹이 > 동물먹이)
    def food_row():
        dv=dc["food"]["amt"]; dpv=dp["food"]["amt"]
        mv=mc["food"]["amt"]; mpv=mp["food"]["amt"]
        yv=yc["food"]["amt"]; ypv=yp["food"]["amt"]
        return _build_dashboard_row(
            "먹이매출",
            _fv(dv,"원"), fyoy(yoy(dv,dpv)),
            _fv(mv,"원"), fyoy(yoy(mv,mpv)),
            _fv(yv,"원"), fyoy(yoy(yv,ypv)),
        )

    # 점포
    def store_rows():
        rows = []
        for k, lbl in STORE_KEYS:
            dv  = shops_dc.get(k,{}).get("amt",0); dpv = shops_dp.get(k,{}).get("amt",0)
            mv  = shops_mc.get(k,{}).get("amt",0); mpv = shops_mp.get(k,{}).get("amt",0)
            yv  = shops_yc.get(k,{}).get("amt",0); ypv = shops_yp.get(k,{}).get("amt",0)
            rows.append(_build_dashboard_row(
                lbl,
                _fv(dv,"원"), fyoy(yoy(dv,dpv)),
                _fv(mv,"원"), fyoy(yoy(mv,mpv)),
                _fv(yv,"원"), fyoy(yoy(yv,ypv)),
            ))
        return rows

    # 전체매출 (점포별 매출 합계 + 네이버/LS 온라인 추정매출)
    all_dc=sum(v["amt"] for v in shops_dc.values())+dc["online_rev"]["naver"]+dc["online_rev"]["ls"]
    all_dp=sum(v["amt"] for v in shops_dp.values())+dp["online_rev"]["naver"]+dp["online_rev"]["ls"]
    all_mc=sum(v["amt"] for v in shops_mc.values())+mc["online_rev"]["naver"]+mc["online_rev"]["ls"]
    all_mp=sum(v["amt"] for v in shops_mp.values())+mp["online_rev"]["naver"]+mp["online_rev"]["ls"]
    all_yc=sum(v["amt"] for v in shops_yc.values())+yc["online_rev"]["naver"]+yc["online_rev"]["ls"]
    all_yp=sum(v["amt"] for v in shops_yp.values())+yp["online_rev"]["naver"]+yp["online_rev"]["ls"]
    total_row = _build_dashboard_row(
        "전체매출",
        _fv(all_dc,"원"), fyoy(yoy(all_dc,all_dp)),
        _fv(all_mc,"원"), fyoy(yoy(all_mc,all_mp)),
        _fv(all_yc,"원"), fyoy(yoy(all_yc,all_yp)),
        grand_total=True,
    )

    return {
        "today_date": f"{today.strftime('%Y-%m-%d')} ({WEEKDAY_KO[today.weekday()]})",
        "prev_date":  f"{ptd.strftime('%Y-%m-%d')} ({WEEKDAY_KO[ptd.weekday()]})",
        "today_weather": {"desc": weather_today[0], "tmax": weather_today[1], "tmin": weather_today[2]},
        "prev_weather":  {"desc": weather_ptd[0],   "tmax": weather_ptd[1],   "tmin": weather_ptd[2]},
        "kpi": {
            "daily_sales":         f"{fmt_num(all_dc)}",
            "daily_visitors":      f"{fmt_num(dc['admission']['individual'] + dc['admission']['group'])}",
            "ytd_sales":           f"{fmt_num(all_yc)}",
            "daily_sales_yoy":     fyoy(yoy(all_dc, all_dp)),
            "daily_visitors_yoy":  fyoy(yoy(
                dc["admission"]["individual"] + dc["admission"]["group"],
                dp["admission"]["individual"] + dp["admission"]["group"],
            )),
            "ytd_sales_yoy":       fyoy(yoy(all_yc, all_yp)),
        },
        "rows": [
            *adm_rows(),
            {"separator": True},
            *adm_rev_rows(),
            {"separator": True},
            food_row(),
            {"separator": True},
            *store_rows(),
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

    print("=== Current year shop ===")
    dc["shops"] = fetch_shop_sales(sess, fmt_d(today), fmt_d(today))
    mc["shops"] = fetch_shop_sales(sess, fmt_d(ms),    fmt_d(today))
    yc["shops"] = fetch_shop_sales(sess, fmt_d(ys),    fmt_d(today))

    print("=== Previous year ===")
    tn, tv = get_api_token(sess)
    dp = fetch_sales(sess, tn, tv, fmt_d(ptd), fmt_d(ptd))
    tn, tv = get_api_token(sess)
    mp = fetch_sales(sess, tn, tv, fmt_d(pms), fmt_d(ptd))
    yp = fetch_sales_chunked(sess, fmt_d(pys), fmt_d(ptd))

    print("=== Previous year shop ===")
    dp["shops"] = fetch_shop_sales(sess, fmt_d(ptd),  fmt_d(ptd))
    mp["shops"] = fetch_shop_sales(sess, fmt_d(pms),  fmt_d(ptd))
    yp["shops"] = fetch_shop_sales(sess, fmt_d(pys),  fmt_d(ptd))

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
