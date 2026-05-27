import asyncio
import os
import re
import xml.etree.ElementTree as ET
from datetime import date, timedelta

import requests
import telegram

BASE_URL   = "https://kis.okpos.co.kr"
LOGIN_URL  = BASE_URL + "/login/login_check.jsp"
API_URL    = BASE_URL + "/sale/sale/ddd.htmlSheetAction"

USER_ID    = os.environ["KIS_ID"]
USER_PW    = os.environ["KIS_PW"]
BOT_TOKEN  = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID    = os.environ["TELEGRAM_CHAT_ID"]

STORE_LABELS = {
    "매표소":       "입장객",
    "카페테리아":   "카페테리아",
    "레스토랑":     "레스토랑",
    "레스토랑신규": "레스토랑신규",
    "열린매대":     "열린매대",
    "무인점포":     "무인점포",
    "먹이판마":     "먹이판매",
    "드론체험":     "드론체험",
    "장난감":       "장난감",
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
        "Referer": BASE_URL + "/login/login_form.jsp",
    })
    # Get login page first (set cookies + CSRF token)
    form_resp = session.get(BASE_URL + "/login/login_form.jsp", verify=False)
    form_html = form_resp.text

    # Extract hidden CSRF/token field
    hidden_match = re.search(r'<input[^>]+type=["']hidden["'][^>]+name=["']([^"']+)["'][^>]+value=["']([^"']*)["']', form_html)
    token_data = {}
    if hidden_match:
        token_name = hidden_match.group(1)
        token_value = hidden_match.group(2)
        token_data = {token_name: token_value}
        print(f"Token found: {token_name[:20]}...")
    else:
        print("No hidden token found")

    # POST login with token
    login_data = {
        "user_id": USER_ID,
        "user_pwd": USER_PW,
        "AutoFg": "W",
        **token_data,
    }
    resp = session.post(LOGIN_URL, data=login_data, allow_redirects=True, verify=False)
    print(f"Login status: {resp.status_code}, URL: {resp.url}")
    print(f"Response: {resp.text[:100]}")

    # Access main page to init session
    session.get(BASE_URL + "/login/top_frame.jsp", verify=False)
    return session

def fetch_data(session, date_from, date_to):
    """Fetch IBSheet data via direct API call"""
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
        "cls_sel": "전체",
        "jum_sel": "전체",
        "deal_sel": "전체",
        "noprd_fg": "N",
        "view_cnt": "100",
        "SheetName": "mySheet1",
    }
    headers = {
        "Referer": BASE_URL + "/sale/sale/prod011.jsp",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
    }
    resp = session.post(API_URL, data=payload, headers=headers, verify=False)
    print(f"API status: {resp.status_code}, length: {len(resp.text)}")
    print(f"Response preview: {resp.text[:200]}")
    return resp.text

def parse_xml(xml_text):
    """Parse IBSheet XML response"""
    if not xml_text or len(xml_text) < 10:
        return {}
    try:
        # IBSheet response format: XML with Row elements
        root = ET.fromstring(xml_text)
        result = {}
        for row in root.iter("Row"):
            c3 = row.get("C3", "")
            if "소계" not in c3:
                continue
            name = re.sub(r"소계\s*:\s*", "", c3).strip()
            qty = float(row.get("C13", "0").replace(",", "") or "0")
            sales = float(row.get("C17", "0").replace(",", "") or "0")
            yoy_raw = row.get("C27", "")
            yoy = float(yoy_raw) if yoy_raw else None
            result[name] = {"qty": qty, "sales": sales, "yoy": yoy}
        print(f"Parsed {len(result)} store entries: {list(result.keys())}")
        return result
    except Exception as e:
        print(f"Parse error: {e}")
        return {"_error": str(e)}

def fmt_num(n):
    if n is None:
        return "N/A"
    return f"{int(n):,}"

def fmt_yoy(yoy):
    if yoy is None:
        return "N/A"
    sign = "+" if yoy >= 0 else ""
    return f"{sign}{yoy:.1f}%"

def build_message(today, daily, monthly, yearly):
    yesterday = today - timedelta(days=1)
    lines = []
    lines.append(f"\U0001f4ca 쥬쥬랜드 매출 리포트")
    lines.append(f"[{today.strftime('%Y-%m-%d')} 기준]")
    lines.append("")

    sections = [
        (f"\U0001f4c5 일별 ({yesterday.strftime('%m/%d')})", daily),
        (f"\U0001f4c6 월누계 ({today.strftime('%m')}월)", monthly),
        (f"\U0001f4c8 연누계 ({today.year}년)", yearly),
    ]

    for sec_name, data in sections:
        lines.append(f"━━━ {sec_name} ━━━")
        if not data or "_error" in data or not data:
            err = data.get("_error", "")[:50] if data and "_error" in data else ""
            lines.append(f"  조회 결과 없음{' (' + err + ')' if err else ''}")
            lines.append("")
            continue

        entry = data.get("매표소", {})
        qty = entry.get("qty", 0)
        yoy = entry.get("yoy")
        lines.append(f"\U0001f465 입장객: {fmt_num(qty)}명  전년비 {fmt_yoy(yoy)}")

        feed = data.get("먹이판마", data.get("먹이판매", {}))
        fsales = feed.get("sales", 0)
        fyoy = feed.get("yoy")
        lines.append(f"\U0001f43e 먹이판매: {fmt_num(fsales)}원  전년비 {fmt_yoy(fyoy)}")

        total_sales = 0
        store_lines = []
        for raw_key, label in STORE_LABELS.items():
            if raw_key == "매표소":
                continue
            item = data.get(raw_key, {})
            s = item.get("sales", 0)
            total_sales += s
            sy = item.get("yoy")
            store_lines.append(f"  - {label}: {fmt_num(s)}원 ({fmt_yoy(sy)})")

        lines.append(f"\U0001f3ea 점포별 합계: {fmt_num(total_sales)}원")
        lines.extend(store_lines)
        lines.append("")

    return "\n".join(lines)

async def main():
    import urllib3
    urllib3.disable_warnings()

    today = date.today()
    d_range, m_range, y_range = get_date_ranges(today)

    session = do_login()

    print(f"Fetching daily: {d_range}")
    raw = fetch_data(session, *d_range)
    daily = parse_xml(raw)

    print(f"Fetching monthly: {m_range}")
    raw = fetch_data(session, *m_range)
    monthly = parse_xml(raw)

    print(f"Fetching yearly: {y_range}")
    raw = fetch_data(session, *y_range)
    yearly = parse_xml(raw)

    msg = build_message(today, daily, monthly, yearly)
    print("=== MESSAGE ===")
    print(msg)
    print("===============")

    bot = telegram.Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=msg)
    print("Telegram sent!")

if __name__ == "__main__":
    asyncio.run(main())
