import asyncio
import os
import re
import xml.etree.ElementTree as ET
from datetime import date, timedelta

import requests
import telegram

BASE_URL   = "https://kis.okpos.co.kr"
LOGIN_URL  = BASE_URL + "/login/login_check.jsp"
FORM_URL   = BASE_URL + "/login/login_form.jsp"
API_URL    = BASE_URL + "/sale/sale/ddd.htmlSheetAction"

USER_ID    = os.environ["KIS_ID"]
USER_PW    = os.environ["KIS_PW"]
BOT_TOKEN  = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID    = os.environ["TELEGRAM_CHAT_ID"]

STORE_LABELS = {
    "\ub9e4\ud45c\uc18c":       "\uc785\uc7a5\uac1d",
    "\uce74\ud398\ud14c\ub9ac\uc544":   "\uce74\ud398\ud14c\ub9ac\uc544",
    "\ub808\uc2a4\ud1a0\ub791":     "\ub808\uc2a4\ud1a0\ub791",
    "\ub808\uc2a4\ud1a0\ub791\uc2e0\uaddc": "\ub808\uc2a4\ud1a0\ub791\uc2e0\uaddc",
    "\uc5f4\ub9b0\ub9e4\ub300":     "\uc5f4\ub9b0\ub9e4\ub300",
    "\ubb34\uc778\uc810\ud3ec":     "\ubb34\uc778\uc810\ud3ec",
    "\uba39\uc774\ud310\ub9c8":     "\uba39\uc774\ud310\ub9e4",
    "\ub4dc\ub860\uccb4\ud5d8":     "\ub4dc\ub860\uccb4\ud5d8",
    "\uc7a5\ub09c\uac10":       "\uc7a5\ub09c\uac10",
}

def get_date_ranges(today):
    yesterday = today - timedelta(days=1)
    yf = yesterday.strftime
    tf = today.strftime
    prev = today.replace(year=today.year - 1)
    pf = prev.strftime
    d_range = (yf("%Y-%m-%d"), yf("%Y-%m-%d"))
    m_range = (today.replace(day=1).strftime("%Y-%m-%d"), tf("%Y-%m-%d"))
    y_range = (pf("%Y-01-01"), pf("%Y-%m-%d"))
    return d_range, m_range, y_range

def do_login():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    })
    # Get login page (sets cookies, get hidden token)
    form_resp = session.get(FORM_URL, verify=False)
    form_html = form_resp.text

    # Find hidden CSRF token: name is a GUID-like value
    token_data = {}
    # Find all hidden inputs
    for m in re.finditer(r'name="([^"]+)"[^>]+type="hidden"', form_html):
        token_data[m.group(1)] = ""
    for m in re.finditer(r'type="hidden"[^>]+name="([^"]+)"[^>]+value="([^"]*)"', form_html):
        token_data[m.group(1)] = m.group(2)
    print(f"Token keys: {list(token_data.keys())[:3]}")

    login_data = {
        "user_id": USER_ID,
        "user_pwd": USER_PW,
        "AutoFg": "W",
        **token_data,
    }
    resp = session.post(LOGIN_URL, data=login_data, allow_redirects=True, verify=False)
    print(f"Login status: {resp.status_code}, URL: {resp.url}")
    if resp.text:
        print(f"Login resp: {resp.text[:100]}")

    session.get(BASE_URL + "/login/top_frame.jsp", verify=False)
    return session

def fetch_data(session, date_from, date_to):
    payload = {
        "sheetjs": "mySheet1",
        "Act": "search",
        "date1_1": date_from,
        "date1_2": date_to,
        "cls_cd": "",
        "mid_cls_cd": "",
        "sm_cls_cd": "",
        "prod_cd": "",
        "prod_nm": "",
        "cls_sel": "\uc804\uccb4",
        "jum_sel": "\uc804\uccb4",
        "deal_sel": "\uc804\uccb4",
        "noprd_fg": "N",
        "view_cnt": "100",
        "SheetName": "mySheet1",
    }
    headers = {
        "Referer": BASE_URL + "/sale/sale/prod011.jsp",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    resp = session.post(API_URL, data=payload, headers=headers, verify=False)
    print(f"API status: {resp.status_code}, len: {len(resp.text)}")
    print(f"Preview: {resp.text[:100]}")
    return resp.text

def parse_xml(xml_text):
    if not xml_text or len(xml_text) < 10:
        return {}
    try:
        root = ET.fromstring(xml_text)
        result = {}
        for row in root.iter("Row"):
            c3 = row.get("C3", "")
            if "\uc18c\uacc4" not in c3:
                continue
            name = re.sub(r"\uc18c\uacc4\s*:\s*", "", c3).strip()
            qty = float((row.get("C13", "0") or "0").replace(",", ""))
            sales = float((row.get("C17", "0") or "0").replace(",", ""))
            yoy_raw = row.get("C27", "")
            yoy = float(yoy_raw) if yoy_raw else None
            result[name] = {"qty": qty, "sales": sales, "yoy": yoy}
        print(f"Parsed {len(result)} entries: {list(result.keys())[:5]}")
        return result
    except Exception as e:
        print(f"Parse error: {e}")
        return {"_error": str(e)}

def fmt_num(n):
    if n is None: return "N/A"
    return f"{int(n):,}"

def fmt_yoy(yoy):
    if yoy is None: return "N/A"
    sign = "+" if yoy >= 0 else ""
    return f"{sign}{yoy:.1f}%"

def build_message(today, daily, monthly, yearly):
    yesterday = today - timedelta(days=1)
    lines = []
    lines.append(f"\U0001f4ca \uc8fc\uc8fc\ub79c\ub4dc \ub9e4\ucd9c \ub9ac\ud3ec\ud2b8")
    lines.append(f"[{today.strftime('%Y-%m-%d')} \uae30\uc900]")
    lines.append("")
    sections = [
        (f"\U0001f4c5 \uc77c\ubcc4 ({yesterday.strftime('%m/%d')})", daily),
        (f"\U0001f4c6 \uc6d4\ub204\uacc4 ({today.strftime('%m')}\uc6d4)", monthly),
        (f"\U0001f4c8 \uc5f0\ub204\uacc4 ({today.year}\ub144)", yearly),
    ]
    for sec_name, data in sections:
        lines.append(f"\u2501\u2501\u2501 {sec_name} \u2501\u2501\u2501")
        if not data or "_error" in data or len(data) == 0:
            err = data.get("_error", "")[:40] if data and "_error" in data else ""
            lines.append(f"  \uc870\ud68c \uacb0\uacfc \uc5c6\uc74c{'('+err+')' if err else ''}")
            lines.append("")
            continue
        entry = data.get("\ub9e4\ud45c\uc18c", {})
        lines.append(f"\U0001f465 \uc785\uc7a5\uac1d: {fmt_num(entry.get('qty',0))}\uba85  \uc804\ub144\ube44 {fmt_yoy(entry.get('yoy'))}")
        feed = data.get("\uba39\uc774\ud310\ub9c8", data.get("\uba39\uc774\ud310\ub9e4", {}))
        lines.append(f"\U0001f43e \uba39\uc774\ud310\ub9e4: {fmt_num(feed.get('sales',0))}\uc6d0  \uc804\ub144\ube44 {fmt_yoy(feed.get('yoy'))}")
        total = 0
        slines = []
        for k, lbl in STORE_LABELS.items():
            if k == "\ub9e4\ud45c\uc18c": continue
            item = data.get(k, {})
            s = item.get("sales", 0)
            total += s
            slines.append(f"  - {lbl}: {fmt_num(s)}\uc6d0 ({fmt_yoy(item.get('yoy'))})")
        lines.append(f"\U0001f3ea \uc810\ud3ec\ubcc4 \ud569\uacc4: {fmt_num(total)}\uc6d0")
        lines.extend(slines)
        lines.append("")
    return "\n".join(lines)

async def main():
    import urllib3
    urllib3.disable_warnings()
    today = date.today()
    d_range, m_range, y_range = get_date_ranges(today)
    session = do_login()
    print(f"Fetching daily: {d_range}")
    daily = parse_xml(fetch_data(session, *d_range))
    print(f"Fetching monthly: {m_range}")
    monthly = parse_xml(fetch_data(session, *m_range))
    print(f"Fetching yearly: {y_range}")
    yearly = parse_xml(fetch_data(session, *y_range))
    msg = build_message(today, daily, monthly, yearly)
    print("=== MESSAGE ===\n" + msg + "\n===============")
    bot = telegram.Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=msg)
    print("Telegram sent!")

if __name__ == "__main__":
    asyncio.run(main())
