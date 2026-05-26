import asyncio
import os
from datetime import date
from playwright.async_api import async_playwright
import telegram

LOGIN_URL = "https://kis.okpos.co.kr/login/login_form.jsp"
USER_ID   = os.environ["KIS_ID"]
USER_PW   = os.environ["KIS_PW"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]

STORE_LABELS = {
    "매표소":       "🎟 입장객",
    "카페테리아":   "☕ 카페테리아",
    "레스토랑":     "🍜 레스토랑",
    "레스토랑신규": "🍽 레스토랑신규",
    "열린매대":     "🛒 열린매대",
    "무인점포":     "🤖 무인점포",
    "먹이판매":     "🐟 먹이판매",
    "드론체험":     "🚁 드론체험",
    "장난감":       "🧸 장난감",
}

def get_date_ranges(today):
    tf = today.strftime
    d_range = (tf("%Y-%m-%d"), tf("%Y-%m-%d"))
    m_range = (today.replace(day=1).strftime("%Y-%m-%d"), tf("%Y-%m-%d"))
    y_range = (today.replace(month=1, day=1).strftime("%Y-%m-%d"), tf("%Y-%m-%d"))
    prev = today.replace(year=today.year - 1)
    pf = prev.strftime
    pd_range = (pf("%Y-%m-%d"), pf("%Y-%m-%d"))
    pm_range = (prev.replace(day=1).strftime("%Y-%m-%d"), pf("%Y-%m-%d"))
    py_range = (prev.replace(month=1, day=1).strftime("%Y-%m-%d"), pf("%Y-%m-%d"))
    return (d_range, m_range, y_range), (pd_range, pm_range, py_range)

PARSE_JS = """() => {
    const sheet = window.mySheet1;
    if (!sheet) return null;
    const xml = sheet.GetXmlData();
    const parser = new DOMParser();
    const doc = parser.parseFromString(xml, 'text/xml');
    const result = {};
    Array.from(doc.querySelectorAll('I[Added="1"]')).forEach(row => {
        const c3 = row.getAttribute('C3') || '';
        if (!c3.includes('소계 :')) return;
        const name = c3.replace('소계 : ', '').trim();
        result[name] = {
            qty: parseInt(row.getAttribute('C13') || '0'),
            revenue: parseInt(row.getAttribute('C15') || '0'),
            net: parseInt(row.getAttribute('C17') || '0'),
        };
    });
    return result;
}"""

async def fetch(prod_frame, date_from, date_to):
    await prod_frame.fill("#date1_1", date_from)
    await prod_frame.fill("#date1_2", date_to)
    await prod_frame.evaluate("() => fnSearch()")
    await prod_frame.wait_for_timeout(4000)
    return await prod_frame.evaluate(PARSE_JS) or {}

def fmt(n):
    return f"{n:,}"

def growth(cur, prev_val):
    if prev_val == 0:
        return "(전년없음)"
    pct = (cur - prev_val) / prev_val * 100
    arrow = "▲" if pct >= 0 else "▼"
    return f"{arrow}{abs(pct):.1f}%"

def section(title, data, prev):
    lines = [f"*{title}*"]
    for store_key, label in STORE_LABELS.items():
        d = data.get(store_key, {})
        qty = d.get("qty", 0)
        net = d.get("net", 0)
        if qty == 0 and net == 0:
            continue
        p = prev.get(store_key, {})
        g = growth(net, p.get("net", 0))
        lines.append(f"  {label}: {fmt(qty)}건  {fmt(net)}원  {g}")
    total = sum(v.get("net", 0) for v in data.values())
    p_total = sum(v.get("net", 0) for v in prev.values())
    g_total = growth(total, p_total)
    lines.append(f"  💰 *총 실매출: {fmt(total)}원  {g_total}*")
    return "\n".join(lines)

def build_message(today, daily, monthly, yearly, pd, pm, py):
    today_str = today.strftime("%Y년 %m월 %d일")
    parts = [
        "🦁 *쥬쥬랜드 일일 실적 보고*",
        f"📅 {today_str}",
        "",
        section("📆 일별", daily, pd),
        "",
        section("📅 월누계", monthly, pm),
        "",
        section("📊 연누계", yearly, py),
    ]
    return "\n".join(parts)

async def main():
    today = date.today()
    (d_range, m_range, y_range), (pd_range, pm_range, py_range) = get_date_ranges(today)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(locale="ko-KR")
        page = await ctx.new_page()

        await page.goto(LOGIN_URL, wait_until="networkidle")
        await page.fill("input[placeholder='아이디']", USER_ID)
        await page.fill("input[type='password']", USER_PW)
        await page.click("button:has-text('로그인')")
        await page.wait_for_timeout(4000)

        for frame in page.frames:
            try:
                btn = await frame.query_selector("button:has-text('닫기')")
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(1000)
                    break
            except Exception:
                pass

        for frame in page.frames:
            try:
                await frame.click("text=매출관리", timeout=3000)
                await page.wait_for_timeout(500)
                await frame.click("text=매출현황", timeout=3000)
                await page.wait_for_timeout(500)
                await frame.click("text=상품별", timeout=3000)
                await page.wait_for_timeout(3000)
                break
            except Exception:
                continue

        prod_frame = None
        for _ in range(10):
            for frame in page.frames:
                if "prod011" in frame.url:
                    prod_frame = frame
                    break
            if prod_frame:
                break
            await page.wait_for_timeout(1000)

        if not prod_frame:
            raise Exception("prod011 frame not found")

        print("prod011 frame found")

        daily        = await fetch(prod_frame, *d_range)
        monthly      = await fetch(prod_frame, *m_range)
        yearly       = await fetch(prod_frame, *y_range)
        prev_daily   = await fetch(prod_frame, *pd_range)
        prev_monthly = await fetch(prod_frame, *pm_range)
        prev_yearly  = await fetch(prod_frame, *py_range)

        await browser.close()

    message = build_message(today, daily, monthly, yearly, prev_daily, prev_monthly, prev_yearly)
    print(message)

    bot = telegram.Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")
    print("Telegram sent!")

if __name__ == "__main__":
    asyncio.run(main())
