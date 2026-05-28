import asyncio
import json
import os
import re
from datetime import date, timedelta

import requests
import telegram
import urllib3

urllib3.disable_warnings()

BASE_URL = "https://kis.okpos.co.kr"
API_URL  = BASE_URL + "/sale/sale/ddd.htmlSheetAction"

USER_ID   = os.environ["KIS_ID"]
USER_PW   = os.environ["KIS_PW"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]

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
    return None, None


def do_login():
    sess = requests.Session()
    sess.headers.update(HEADERS)
    r1 = sess.post(
        BASE_URL + "/login/login_check.jsp",
        data={"user_id": USER_ID, "user_pwd": USER_PW, "AutoFg": "W"},
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
    print(f"prod010 token: {tok10n[:8]}...")
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
        "ss_SIZE_CLS_CD": "", "ss_CLS_TEXT": "전체",
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
    agg = {}
    for row in rows:
        cat = row.get("MCLS_NM") or row.get("LCLS_NM") or "기타"
        qty = int(row.get("SALE_QTY", 0) or 0)
        amt = int(row.get("TOT_SALE_AMT", 0) or 0)
        if cat not in agg:
            agg[cat] = {"qty": 0, "amt": 0}
        agg[cat]["qty"] += qty
        agg[cat]["amt"] += amt
    print(f"  Categories: {list(agg.keys())}")
    return agg

def yoy(curr, prev):
    if not prev:
        return None
    return (curr - prev) / prev * 100


def fmt(n):
    return f"{int(n):,}"


def fyoy(v):
    if v is None:
        return "N/A"
    return f"{'+' if v >= 0 else ''}{v:.1f}%"


def section(title, curr, prev):
    lines = [f"━━ {title} ━━"]
    adm = curr.get("매표소", {})
    padm = prev.get("매표소", {})
    aq, paq = adm.get("qty", 0), padm.get("qty", 0)
    lines.append(f"U0001f465 입장객: {fmt(aq)}명  전년비 {fyoy(yoy(aq, paq))}")
    fd = curr.get("열린매대", {})
    pfd = prev.get("열린매대", {})
    fa, pfa = fd.get("amt", 0), pfd.get("amt", 0)
    lines.append(f"U0001f43e 먹이판매: {fmt(fa)}원  전년비 {fyoy(yoy(fa, pfa))}")
    cats = [
        ("레스토랑", "레스토랑"),
        ("카페테리아", "카페테리아"),
        ("레스토랑신규", "레스토랑신규"),
        ("무인점포", "무인점포"),
        ("드론체험", "드론체험"),
        ("베이커리", "베이커리"),
    ]
    tc, tp = 0, 0
    sl = []
    for k, lbl in cats:
        c = curr.get(k, {})
        p = prev.get(k, {})
        ca, pa = c.get("amt", 0), p.get("amt", 0)
        tc += ca
        tp += pa
        sl.append(f"  - {lbl}: {fmt(ca)}원 ({fyoy(yoy(ca, pa))})")
    lines.append(f"U0001f3ea 점포합계: {fmt(tc)}원  전년비 {fyoy(yoy(tc, tp))}")
    lines.extend(sl)
    return lines

async def main():
    today = date.today()
    yd = today - timedelta(days=1)
    pyd = yd.replace(year=yd.year - 1)
    ms = today.replace(day=1)
    pms = ms.replace(year=ms.year - 1)
    ys = today.replace(month=1, day=1)
    pys = ys.replace(year=ys.year - 1)
    fmt_d = lambda d: d.strftime("%Y-%m-%d")

    sess = do_login()

    print("=== Current year ===")
    tn, tv = get_api_token(sess)
    dc = fetch_sales(sess, tn, tv, fmt_d(yd), fmt_d(yd))
    tn, tv = get_api_token(sess)
    mc = fetch_sales(sess, tn, tv, fmt_d(ms), fmt_d(yd))
    tn, tv = get_api_token(sess)
    yc = fetch_sales(sess, tn, tv, fmt_d(ys), fmt_d(yd))

    print("=== Previous year ===")
    tn, tv = get_api_token(sess)
    dp = fetch_sales(sess, tn, tv, fmt_d(pyd), fmt_d(pyd))
    tn, tv = get_api_token(sess)
    mp = fetch_sales(sess, tn, tv, fmt_d(pms), fmt_d(pyd))
    tn, tv = get_api_token(sess)
    yp = fetch_sales(sess, tn, tv, fmt_d(pys), fmt_d(pyd))

    lines = [
        f"U0001f4ca 주주랜드 매출 리포트  [{today.strftime('%Y-%m-%d')} 기준]",
        "",
    ]
    lines += section(f"U0001f4c5 일별 ({yd.strftime('%m/%d')})", dc, dp)
    lines.append("")
    lines += section(f"U0001f4c6 월누계 ({today.strftime('%m')}월)", mc, mp)
    lines.append("")
    lines += section(f"U0001f4c8 연누계 ({today.year}년)", yc, yp)

    msg = "
".join(lines)
    print("=== MESSAGE ===")
    print(msg)
    print("===============")

    bot = telegram.Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=msg)
    print("Sent!")


if __name__ == "__main__":
    asyncio.run(main())
