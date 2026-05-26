import asyncio
import os
from datetime import date
from playwright.async_api import async_playwright
import telegram

LOGIN_URL = "https://kis.okpos.co.kr/login/login_form.jsp"
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
    tf = today.strftime
    d_range = (tf("%Y-%m-%d"), tf("%Y-%m-%d"))
    m_range = (today.replace(day=1).strftime("%Y-%m-%d"), tf("%Y-%m-%d"))
    prev = today.replace(year=today.year - 1)
    pf = prev.strftime
    y_range = (pf("%Y-01-01"), pf("%Y-%m-%d"))
    return d_range, m_range, y_range

PARSE_JS = """
() => {
    try {
        const xml = mySheet1.GetXmlData();
        if (!xml) return {};
        const parser = new DOMParser();
        const doc = parser.parseFromString(xml, "text/xml");
        const rows = doc.querySelectorAll("Row");
        const result = {};
        for (const row of rows) {
            const c3 = row.getAttribute("C3") || "";
            if (!c3.includes("소계")) continue;
            const name = c3.replace(/소계\\s*:\\s*/, "").trim();
            const qty = parseFloat(row.getAttribute("C13") || "0") || 0;
            const sales = parseFloat((row.getAttribute("C17") || "0").replace(/,/g, "")) || 0;
            const yoy_raw = row.getAttribute("C27") || "";
            const yoy = yoy_raw !== "" ? parseFloat(yoy_raw) : null;
            result[name] = { qty, sales, yoy };
        }
        return result;
    } catch(e) {
        return { _error: e.toString() };
    }
}
""";

async def do_login(page):
    found = False
    for frame in page.frames:
        try:
            el = await frame.query_selector("input[placeholder='아이디']")
            if el:
                await frame.fill("input[placeholder='아이디']", USER_ID)
                await frame.fill("input[type='password']", USER_PW)
                await frame.evaluate("document.querySelector('form').submit()")
                found = True
                break
        except Exception:
            continue
    if not found:
        raise RuntimeError("로그인 폼을 찾을 수 없습니다")
    await page.wait_for_timeout(3000)

async def close_popup(page):
    await page.wait_for_timeout(2000)
    for frame in page.frames:
        try:
            btns = await frame.query_selector_all("button, a, input[type='button']")
            for btn in btns:
                txt = (await btn.inner_text()).strip()
                if txt in ["닫기", "확인", "취소", "나중에", "Close", "X", "×"]:
                    await btn.click()
                    await page.wait_for_timeout(500)
                    break
        except Exception:
            continue

async def navigate_to_prod(page):
    await page.wait_for_timeout(2000)
    clicked = False
    for frame in page.frames:
        try:
            links = await frame.query_selector_all("a, li, td, div")
            for el in links:
                txt = (await el.inner_text()).strip()
                if "매출관리" in txt and len(txt) < 20:
                    await el.click()
                    clicked = True
                    break
        except Exception:
            continue
        if clicked:
            break
    await page.wait_for_timeout(1500)

    clicked = False
    for frame in page.frames:
        try:
            links = await frame.query_selector_all("a, li, td, div")
            for el in links:
                txt = (await el.inner_text()).strip()
                if "매출현황" in txt and len(txt) < 20:
                    await el.click()
                    clicked = True
                    break
        except Exception:
            continue
        if clicked:
            break
    await page.wait_for_timeout(1500)

    clicked = False
    for frame in page.frames:
        try:
            links = await frame.query_selector_all("a, li, td, div")
            for el in links:
                txt = (await el.inner_text()).strip()
                if "상품별" in txt and len(txt) < 20:
                    await el.click()
                    clicked = True
                    break
        except Exception:
            continue
        if clicked:
            break
    await page.wait_for_timeout(2000)

async def get_prod_frame(page):
    for _ in range(20):
        for frame in page.frames:
            if "prod011" in (frame.url or ""):
                return frame
        await page.wait_for_timeout(500)
    raise RuntimeError("prod011 프레임을 찾을 수 없습니다")

async def fetch(prod_frame, date_from, date_to):
    await prod_frame.evaluate(f"""
        (() => {{
            const d1 = document.getElementById('date1_1');
            const d2 = document.getElementById('date1_2');
            if (d1) d1.value = '{date_from}';
            if (d2) d2.value = '{date_to}';
        }})()
    """)
    await prod_frame.wait_for_timeout(500)
    await prod_frame.evaluate("() => fnSearch()")
    await prod_frame.wait_for_timeout(6000)
    return await prod_frame.evaluate(PARSE_JS) or {}

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
    lines = []
    lines.append(f"📊 쥬쥬랜드 매출 리포트 [{today.strftime('%Y-%m-%d')}]")
    lines.append("")

    sections = [
        ("📅 일별", daily),
        ("📆 월누계", monthly),
        ("📈 연누계", yearly),
    ]

    for sec_name, data in sections:
        lines.append(f"━━━ {sec_name} ━━━")
        if not data or "_error" in data:
            lines.append("  데이터 없음")
            lines.append("")
            continue

        entry = data.get("매표소", {})
        qty = entry.get("qty", 0)
        yoy = entry.get("yoy")
        lines.append(f"👥 입장객: {fmt_num(qty)}명  전년비 {fmt_yoy(yoy)}")

        feed = data.get("먹이판마", data.get("먹이판매", {}))
        fsales = feed.get("sales", 0)
        fyoy = feed.get("yoy")
        lines.append(f"🐾 먹이판매: {fmt_num(fsales)}원  전년비 {fmt_yoy(fyoy)}")

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

        lines.append(f"🏪 점포별 합계: {fmt_num(total_sales)}원")
        lines.extend(store_lines)
        lines.append("")

    return "\n".join(lines)

async def main():
    today = date.today()
    d_range, m_range, y_range = get_date_ranges(today)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(LOGIN_URL, wait_until="networkidle", timeout=30000)
        print(f"Login page loaded: {page.url}")

        await do_login(page)
        print(f"Login OK: {page.url}")

        await close_popup(page)

        await navigate_to_prod(page)
        print("Navigation done")

        prod_frame = await get_prod_frame(page)
        print(f"prod_frame found: {prod_frame.url}")

        print(f"Fetching daily: {d_range}")
        daily = await fetch(prod_frame, *d_range)
        print(f"Daily data keys: {list(daily.keys())}")

        print(f"Fetching monthly: {m_range}")
        monthly = await fetch(prod_frame, *m_range)
        print(f"Monthly data keys: {list(monthly.keys())}")

        print(f"Fetching yearly: {y_range}")
        yearly = await fetch(prod_frame, *y_range)
        print(f"Yearly data keys: {list(yearly.keys())}")

        await browser.close()

    msg = build_message(today, daily, monthly, yearly)
    print("Message:")
    print(msg)

    bot = telegram.Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=msg)
    print("Telegram sent!")

if __name__ == "__main__":
    asyncio.run(main())
