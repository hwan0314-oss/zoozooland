import asyncio
import json
import os
import re
import unicodedata
from datetime import date, timedelta, datetime, timezone

import requests
import telegram
import urllib3

urllib3.disable_warnings()

BASE_URL  = "https://kis.okpos.co.kr"
API_URL   = BASE_URL + "/sale/sale/ddd.htmlSheetAction"

USER_ID   = os.environ["KIS_ID"]
USER_PW   = os.environ["KIS_PW"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]

KST = timezone(timedelta(hours=9))

# 상품명에 이 키워드가 포함되면 카테고리 무관하게 먹이판매로 집계
FOOD_KEYWORDS = ["먹이", "양분유체험"]

# 매출 0원이지만 건당 15,000원으로 산정할 온라인 티켓 상품명 (정확히 일치)
ONLINE_TICKETS = {"온라인티켓(LS)", "네이버 주중", "네이버 주말"}
ONLINE_TICKET_PRICE = 15_000

# 무료 입장 상품명 (정확히 일치)
FREE_PRODUCTS = {"24개월미만무료입장", "초대권"}

# 점포매출 집계 대상 카테고리 (API MCLS_NM 값 → 표시 레이블)
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


def extract_token(html):
    m = re.search(
        r"id='([0-9a-f-]{36})'\s+name='([0-9a-f-]{36})'\s+value='([0-9a-f-]{36})'",
        html, re.IGNORECASE,
    )
    if m:
        return m.group(2), m.group(3)
    m = re.search(
        r'name="([0-9a-f-]{36})"[^>]*value="([0-9a-f-]{36})"',
        html, re.IGNORECASE,
    )
    if m:
        return m.group(1), m.group(2)
    m = re.search(
        r'name="([0-9a-f-]{36})"[^>]*value="([^"]+)"',
        html, re.IGNORECASE,
    )
    if m:
        return m.group(1), m.group(2)
    m = re.search(
        r"name='([0-9a-f-]{36})'[^>]*value='([^']+)'",
        html, re.IGNORECASE,
    )
    if m:
        return m.group(1), m.group(2)
    return None, None


def do_login():
    sess = requests.Session()
    sess.headers.update(HEADERS)
    r0 = sess.get(
        BASE_URL + "/login/login_form.jsp",
        verify=False, timeout=30,
    )
    print(f"login_form: {r0.status_code} len={len(r0.text)}")
    form_tok_n, form_tok_v = extract_token(r0.text)
    print(f"form token: {form_tok_n[:8] if form_tok_n else None}...")
    login_data = {"user_id": USER_ID, "user_pwd": USER_PW, "AutoFg": "W"}
    if form_tok_n:
        login_data[form_tok_n] = form_tok_v
    r1 = sess.post(
        BASE_URL + "/login/login_check.jsp",
        data=login_data,
        headers={"Referer": BASE_URL + "/login/login_form.jsp"},
        verify=False, timeout=30,
    )
    print(f"login_check: {r1.status_code} len={len(r1.text)}")
    tok_name, tok_val = extract_token(r1.text)
    if not tok_name:
        raise RuntimeError(f"No CSRF token. HTML: {r1.text[:300]}")
    print(f"CSRF: {tok_name[:8]}...")
    r2 = sess.post(
        BASE_URL + "/login/login_check_action.jsp",
        data={"user_id": USER_ID, "user_pwd": USER_PW, "AutoFg": "W", tok_name: tok_val},
        headers={"Referer": BASE_URL + "/login/login_check.jsp"},
        verify=False, timeout=30,
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
        headers={"Referer": BASE_URL + "/login/top_frame.jsp"},
        verify=False, timeout=30,
    )
    print(f"prod010: {r1.status_code} len={len(r1.text)}")
    tok10n, tok10v = extract_token(r1.text)
    if not tok10n:
        raise RuntimeError(f"No token in prod010. HTML: {r1.text[:300]}")
    r2 = sess.post(
        BASE_URL + "/sale/sale/prod011.jsp",
        data={tok10n: tok10v},
        headers={"Referer": BASE_URL + "/sale/sale/prod010.jsp"},
        verify=False, timeout=30,
    )
    print(f"prod011: {r2.status_code} len={len(r2.text)}")
    if "S_CONTROLLER" not in r2.text:
        raise RuntimeError(f"prod011 bad response. First 200: {r2.text[:200]}")
    tok11n, tok11v = extract_token(r2.text)
    if not tok11n:
        raise RuntimeError("No token in prod011")
    print(f"prod011 token: {tok11n[:8]}...")
    return tok11n, tok11v


def fetch_sales(sess, tok_name, tok_val, date_from, date_to):
    payload = {
        tok_name: tok_val,
        "S_CONTROLLER": "sale.sale.prod011",
        "S_METHOD": "search",
        "SHEETSEQ": "1",
        "S_SAVENAME": S_SAVENAME,
        "S_ORDERBY": "",
        "ss_PROD_FG": "N",
        "date1_1": date_from,
        "date1_2": date_to,
        "date_period1": "366",
        "ss_PROD_CD": "", "ss_PROD_NM": "",
        "ss_LCLS_CD": "", "ss_MCLS_CD": "", "ss_SCLS_CD": "",
        "ss_SIZE_CLS_CD": "",
        "ss_CLS_TEXT": "전체",
        "ss_BAR_CD": "", "ss_SHOP_CD": "",
        "ss_SHOP_NM": "전체",
        "ss_SHOP_INFO": "[]", "ss_VENDOR_CD": "",
        "ss_VENDOR_NM": "전체",
        "ss_VENDOR_INFO": "[]", "ss_chk": "0",
        "ss_PAGE_SIZE": "500", "ss_PAGE_NO1": "1",
    }
    r = sess.post(
        API_URL, data=payload,
        headers={"Referer": BASE_URL + "/sale/sale/prod011.jsp"},
        verify=False, timeout=60,
    )
    print(f"API [{date_from}~{date_to}]: {r.status_code} len={len(r.text)}")
    data = json.loads(r.text)
    if "Result" in data and data["Result"].get("Code", 0) < 0:
        raise RuntimeError(f"API error: {data['Result']['Message']}")
    rows = data.get("Data", [])

    cats = {}
    food = {"qty": 0, "amt": 0}
    admission = {"total": 0, "individual": 0, "group": 0, "free": 0}

    for row in rows:
        cat      = row.get("MCLS_NM") or row.get("LCLS_NM") or "기타"
        prod_nm  = (row.get("PROD_NM") or "").strip()
        scls_nm  = (row.get("SCLS_NM") or "").strip()
        qty      = int(row.get("SALE_QTY", 0) or 0)

        # 온라인 티켓은 POS 매출이 0원이므로 건당 고정가 적용
        if prod_nm in ONLINE_TICKETS:
            amt = qty * ONLINE_TICKET_PRICE
        else:
            amt = int(row.get("TOT_SALE_AMT", 0) or 0)

        # 카테고리별 집계
        if cat not in cats:
            cats[cat] = {"qty": 0, "amt": 0}
        cats[cat]["qty"] += qty
        cats[cat]["amt"] += amt

        # 상품명 기반 먹이판매 집계 (카테고리 무관)
        if any(kw in prod_nm for kw in FOOD_KEYWORDS):
            food["qty"] += qty
            food["amt"] += amt

        # 입장객 집계 (매표소 카테고리, 무료/단체/개인 구분)
        if cat == "매표소":
            admission["total"] += qty
            if prod_nm in FREE_PRODUCTS:
                admission["free"] += qty
            elif "단체" in prod_nm or "단체" in scls_nm:
                admission["group"] += qty
            else:
                admission["individual"] += qty

    print(f"  Categories: {list(cats.keys())}")
    return {"cats": cats, "food": food, "admission": admission}


def fetch_sales_chunked(sess, date_from_str, date_to_str, max_days=90):
    start = date.fromisoformat(date_from_str)
    end   = date.fromisoformat(date_to_str)
    total = {
        "cats": {},
        "food": {"qty": 0, "amt": 0},
        "admission": {"total": 0, "individual": 0, "group": 0, "free": 0},
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
        for k in ("total", "individual", "group", "free"):
            total["admission"][k] += chunk["admission"][k]
        current = chunk_end + timedelta(days=1)
    return total


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


def _dw(s: str) -> int:
    """한국어/CJK 문자를 2칸으로 계산한 표시 너비"""
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in s)

def _rpad(s: str, w: int) -> str:
    return s + " " * max(0, w - _dw(s))

def _lpad(s: str, w: int) -> str:
    return " " * max(0, w - _dw(s)) + s


def build_section(title, curr, prev):
    cats_c = curr["cats"];  cats_p = prev["cats"]
    food_c = curr["food"];  food_p = prev["food"]
    adm_c  = curr["admission"]; adm_p = prev["admission"]

    tot_c = adm_c["total"];      tot_p = adm_p["total"]
    ind_c = adm_c["individual"]; ind_p = adm_p["individual"]
    grp_c = adm_c["group"];      grp_p = adm_p["group"]
    fre_c = adm_c["free"];       fre_p = adm_p["free"]
    fa    = food_c["amt"];        pfa   = food_p["amt"]

    tc, tp = 0, 0
    store_rows = []
    for k, lbl in STORE_KEYS:
        ca = cats_c.get(k, {}).get("amt", 0)
        pa = cats_p.get(k, {}).get("amt", 0)
        tc += ca; tp += pa
        store_rows.append((f"  {lbl}", f"{fmt_num(ca)}원", fyoy(yoy(ca, pa))))

    all_c = sum(v["amt"] for v in cats_c.values())
    all_p = sum(v["amt"] for v in cats_p.values())

    # (레이블, 값, 전년비) 순서로 행 구성. None = 구분선
    rows = [
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
        ("전체매출",   f"{fmt_num(all_c)}원", fyoy(yoy(all_c, all_p))),
    ]

    data = [r for r in rows if r is not None]
    hdr  = ("구분", "금액/수량", "전년비")
    all_data = [hdr] + data
    c0 = max(_dw(r[0]) for r in all_data)
    c1 = max(_dw(r[1]) for r in all_data)
    c2 = max(_dw(r[2]) for r in all_data)
    sep = "─" * (c0 + c1 + c2 + 6)

    def fmt_row(r):
        return _rpad(r[0], c0 + 2) + _lpad(r[1], c1 + 2) + _lpad(r[2], c2)

    table = [fmt_row(hdr), sep]
    for row in rows:
        table.append(sep if row is None else fmt_row(row))

    return [f"<b>{title}</b>", "<pre>" + "\n".join(table) + "</pre>"]


async def main():
    today = datetime.now(KST).date()          # 항상 KST 기준
    ms  = today.replace(day=1)                # 이번 달 1일
    pms = ms.replace(year=ms.year - 1)        # 전년 동월 1일
    ys  = today.replace(month=1, day=1)       # 올해 1월 1일
    pys = ys.replace(year=ys.year - 1)        # 전년 1월 1일
    ptd = today.replace(year=today.year - 1)  # 전년 동일
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

    header = (
        f"📊 <b>쥬쥬랜드 실적 리포트</b>\n"
        f"📅 <b>{today.strftime('%Y-%m-%d')}</b> 기준"
    )
    lines = [header, ""]
    lines += build_section(f"📅 일별 ({today.strftime('%m/%d')})", dc, dp)
    lines.append("")
    lines += build_section(f"📆 월누계 ({today.strftime('%m')}월)", mc, mp)
    lines.append("")
    lines += build_section(f"📈 연누계 ({today.year}년)", yc, yp)

    msg = "\n".join(lines)
    print("=== MESSAGE ===")
    print(msg)
    print("===============")

    bot = telegram.Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="HTML")
    print("Sent!")


if __name__ == "__main__":
    asyncio.run(main())
