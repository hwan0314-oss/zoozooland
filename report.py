import asyncio
import json
import os
import re
from datetime import date, timedelta

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
        "ss_CLS_TEXT": "\uc804\uccb4",
        "ss_BAR_CD": "", "ss_SHOP_CD": "",
        "ss_SHOP_NM": "\uc804\uccb4",
        "ss_SHOP_INFO": "[]", "ss_VENDOR_CD": "",
        "ss_VENDOR_NM": "\uc804\uccb4",
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
        cat = row.get("MCLS_NM") or row.get("LCLS_NM") or "\uae30\ud0c0"
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


def fmt_num(n):
    return f"{int(n):,}"


def fyoy(v):
    if v is None:
        return "N/A"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.1f}%"


def build_section(title, curr, prev):
    adm = curr.get("\ub9e4\ud45c\uc18c", {})
    padm = prev.get("\ub9e4\ud45c\uc18c", {})
    aq = adm.get("qty", 0)
    paq = padm.get("qty", 0)
    fd = curr.get("\uc5f4\ub9b0\ub9e4\ub300", {})
    pfd = prev.get("\uc5f4\ub9b0\ub9e4\ub300", {})
    fa = fd.get("amt", 0)
    pfa = pfd.get("amt", 0)
    store_keys = [
        ("\ub808\uc2a4\ud1a0\ub791", "\ub808\uc2a4\ud1a0\ub791"),
        ("\uce74\ud398\ud14c\ub9ac\uc544", "\uce74\ud398\ud14c\ub9ac\uc544"),
        ("\ub808\uc2a4\ud1a0\ub791\uc2e0\uaddc", "\ub808\uc2a4\ud1a0\ub791(\uc2e0)"),
        ("\ubb34\uc778\uc810\ud3ec", "\ubb34\uc778\uc810\ud3ec"),
        ("\ub4dc\ub860\uccb4\ud5d8", "\ub4dc\ub860\uccb4\ud5d8"),
        ("\ubca0\uc774\ucee4\ub9ac", "\ubca0\uc774\ucee4\ub9ac"),
    ]
    tc, tp = 0, 0
    sl = []
    for k, lbl in store_keys:
        c = curr.get(k, {})
        p = prev.get(k, {})
        ca = c.get("amt", 0)
        pa = p.get("amt", 0)
        tc += ca
        tp += pa
        sl.append(f"  - {lbl}: {fmt_num(ca)}\uc6d0 ({fyoy(yoy(ca, pa))})")
    result = [
        f"\u2501\u2501 {title} \u2501\u2501",
        f"\U0001f465 \uc785\uc7a5\uac1d: {fmt_num(aq)}\uba85  \uc804\ub144\ube44 {fyoy(yoy(aq, paq))}",
        f"\U0001f43e \uba39\uc774\ud310\ub9e4: {fmt_num(fa)}\uc6d0  \uc804\ub144\ube44 {fyoy(yoy(fa, pfa))}",
        f"\U0001f3ea \uc810\ud3ec\ud569\uacc4: {fmt_num(tc)}\uc6d0  \uc804\ub144\ube44 {fyoy(yoy(tc, tp))}",
    ]
    result.extend(sl)
    return result


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

    header = f"\U0001f4ca \uc8fc\uc8fc\ub7e0\ub4dc \ub9e4\uc6cd \ub9ac\ud3ec\ud2b8 [{today.strftime('%Y-%m-%d')} \uae30\uc900]"
    lines = [header, ""]
    lines += build_section(f"\U0001f4c5 \uc77c\ubcc4 ({yd.strftime('%m/%d')})", dc, dp)
    lines.append("")
    lines += build_section(f"\U0001f4c6 \uc6d4\ub204\uacc4 ({today.strftime('%m')}\uc6d4)", mc, mp)
    lines.append("")
    lines += build_section(f"\U0001f4c8 \uc5f0\ub204\uacc4 ({today.year}\ub144)", yc, yp)

    msg = chr(10).join(lines)
    print("=== MESSAGE ===")
    print(msg)
    print("===============")

    bot = telegram.Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=msg)
    print("Sent!")


if __name__ == "__main__":
    asyncio.run(main())
