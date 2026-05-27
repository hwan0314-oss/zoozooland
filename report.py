import os
import re
import xml.etree.ElementTree as ET
from datetime import date, timedelta

import requests
import telegram

BASE_URL   = "https://kis.okpos.co.kr"
LOGIN_URL  = BASE_URL + "/login/login_check.jsp"
FORM_URL   = BASE_URL + "/login/login_form.jsp"
PROD010    = BASE_URL + "/sale/sale/prod010.jsp"
PROD011    = BASE_URL + "/sale/sale/prod011.jsp"
API_URL    = BASE_URL + "/sale/sale/ddd.htmlSheetAction"

USER_ID    = os.environ["KIS_ID"]
USER_PW    = os.environ["KIS_PW"]
BOT_TOKEN  = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID    = os.environ["TELEGRAM_CHAT_ID"]


def do_login(session):
    r = session.get(FORM_URL, timeout=30)
    print(f"form status: {r.status_code}")
    html = r.text

    token_name, token_val = None, None
    uuid_pat = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.I)
    tag_pat  = re.compile(r'<input[^>]+>', re.I)
    for tag in tag_pat.findall(html):
        if 'hidden' not in tag.lower():
            continue
        nm = re.search(r'name=["\']([^"\' >]+)["\']', tag, re.I)
        vl = re.search(r'value=["\']([^"\' >]+)["\']', tag, re.I)
        if nm and vl and uuid_pat.match(nm.group(1)):
            token_name = nm.group(1)
            token_val  = vl.group(1)
            break

    print(f"Token: {token_name[:8] if token_name else None}")
    payload = {"user_id": USER_ID, "user_pwd": USER_PW, "AutoFg": "W"}
    if token_name:
        payload[token_name] = token_val

    r2 = session.post(LOGIN_URL, data=payload, timeout=30)
    print(f"login status: {r2.status_code}, url: {r2.url}")
    if "login_form" in r2.url or "login_check" in r2.url:
        print("LOGIN FAILED")
        return False
    print("Login SUCCESS")
    return True


def init_prod(session):
    r1 = session.get(PROD010, timeout=30)
    print(f"prod010: {r1.status_code}")
    html = r1.text

    token_name, token_val = None, None
    uuid_pat = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.I)
    tag_pat  = re.compile(r'<input[^>]+>', re.I)
    for tag in tag_pat.findall(html):
        if 'hidden' not in tag.lower():
            continue
        nm = re.search(r'name=["\']([^"\' >]+)["\']', tag, re.I)
        vl = re.search(r'value=["\']([^"\' >]+)["\']', tag, re.I)
        if nm and vl and uuid_pat.match(nm.group(1)):
            token_name = nm.group(1)
            token_val  = vl.group(1)
            break

    print(f"prod010 token: {token_name[:8] if token_name else None}")
    return token_name, token_val


def fetch_data(session, token_name, token_val, date1, date2):
    payload = {
        "S_CONTROLLER": "sale.sale.prod011",
        "S_METHOD":     "search",
        "SHEETSEQ":     "1",
        "S_SAVENAME":   "sSeq|LCLS_NM|MCLS_NM|SCLS_NM|SALE_DATE|PROD_CD|BAR_CD|MAP_PROD_CD|PROD_NM|VENDORS_NM|COLOR_CD|SIZE_STR_CD|SALE_QTY|PROD_WEIGHT|TOT_SALE_AMT|TOT_DC_AMT|DCM_SALE_AMT|DC_AMT_GEN|DC_AMT_SVC|DC_AMT_JCD|DC_AMT_CPN|DC_AMT_CST|DC_AMT_FOD|DC_AMT_PACK|DC_AMT_YAP|SHOP_CD",
        "S_ORDERBY":    "",
        "ss_PROD_FG":   "N",
        "date1_1":      date1,
        "date1_2":      date2,
        "date_period1": "366",
        "ss_PROD_CD":   "",
        "ss_PROD_NM":   "",
        "ss_LCLS_CD":   "",
        "ss_MCLS_CD":   "",
        "ss_SCLS_CD":   "",
        "ss_SIZE_CLS_CD": "",
        "ss_CLS_TEXT":  "\uc804\uccb4",
        "ss_BAR_CD":    "",
        "ss_SHOP_CD":   "",
        "ss_SHOP_NM":   "\uc804\uccb4",
        "ss_SHOP_INFO": "[]",
        "ss_VENDOR_CD": "",
        "ss_VENDOR_NM": "\uc804\uccb4",
        "ss_VENDOR_INFO": "[]",
        "ss_chk":       "0",
        "ss_PAGE_SIZE": "500",
        "ss_PAGE_NO1":  "1",
    }
    if token_name:
        payload[token_name] = token_val

    headers = {"Referer": PROD011}
    r = session.post(API_URL, data=payload, headers=headers, timeout=60)
    print(f"API {date1}~{date2}: status={r.status_code} len={len(r.text)}")
    print(f"Preview: {r.text[:200]}")
    return r.text


def parse_xml(xml_text):
    if xml_text.strip().startswith("{"):
        print(f"API error: {xml_text[:100]}")
        return []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f"Parse error: {e} | text: {xml_text[:100]}")
        return []

    rows = []
    for row in root.iter("Row"):
        a = row.attrib
        shop = a.get("SHOP_NM") or a.get("SHOP_CD") or ""
        if not shop.strip():
            continue
        qty_s = a.get("SALE_QTY", "0")
        rev_s = a.get("DCM_SALE_AMT") or a.get("TOT_SALE_AMT", "0")
        try:
            qty = int(str(qty_s).replace(",","").strip() or 0)
            rev = int(str(rev_s).replace(",","").strip() or 0)
        except ValueError:
            qty, rev = 0, 0
        rows.append({"shop": shop.strip(), "qty": qty, "rev": rev})

    agg = {}
    for r in rows:
        k = r["shop"]
        if k not in agg:
            agg[k] = {"shop": k, "qty": 0, "rev": 0}
        agg[k]["qty"] += r["qty"]
        agg[k]["rev"] += r["rev"]

    result = list(agg.values())
    print(f"Shops: {len(result)}, total rows: {len(rows)}")
    return result


def fmt(n):
    return f"{n:,}" if n else "0"


def build_message(yesterday, d_rows, m_rows, y_rows):
    today = date.today().strftime("%Y-%m-%d")
    ystr  = yesterday.strftime("%Y-%m-%d")
    mstr  = yesterday.strftime("%Y-%m")
    yrstr = yesterday.strftime("%Y")

    lines = [
        "\U0001f4ca \uc8fc\uc8fc\ub79c\ub4dc \ub9e4\ucd9c \ub9ac\ud3ec\ud2b8",
        f"[{today} \uae30\uc900]",
        "",
    ]

    def section(title, rows, label):
        lines.append(f"\u2014\u2014 {title} ({label}) \u2014\u2014")
        if not rows:
            lines.append("  \ub370\uc774\ud130 \uc5c6\uc74c")
        else:
            for s in rows:
                lines.append(f"  {s['shop']}: {fmt(s['qty'])}\uac74 / {fmt(s['rev'])}\uc6d0")
        lines.append("")

    section("\U0001f4c5 \uc77c\ubcc4", d_rows, ystr)
    section("\U0001f5d3 \uc6d4\ub204\uacc4", m_rows, f"{mstr} \ub204\uacc4")
    section("\U0001f4dd \uc5f0\ub204\uacc4", y_rows, f"{yrstr} \ub204\uacc4")
    lines.append("=" * 15)
    return "\n".join(lines)


def main():
    yesterday = date.today() - timedelta(days=1)
    y  = yesterday.strftime("%Y-%m-%d")
    ms = yesterday.strftime("%Y-%m-01")
    ys = yesterday.strftime("%Y-01-01")

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0"})

    do_login(session)
    token_name, token_val = init_prod(session)

    d_xml  = fetch_data(session, token_name, token_val, y,  y)
    m_xml  = fetch_data(session, token_name, token_val, ms, y)
    yr_xml = fetch_data(session, token_name, token_val, ys, y)

    d_rows  = parse_xml(d_xml)
    m_rows  = parse_xml(m_xml)
    yr_rows = parse_xml(yr_xml)

    msg = build_message(yesterday, d_rows, m_rows, yr_rows)
    print("=== MESSAGE ===")
    print(msg)

    import asyncio

    async def send():
        bot = telegram.Bot(token=BOT_TOKEN)
        await bot.send_message(chat_id=CHAT_ID, text=msg)
        print("Telegram sent!")

    asyncio.run(send())


if __name__ == "__main__":
    main()
