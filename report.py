import asyncio
import os
from datetime import date
from playwright.async_api import async_playwright
import telegram

# ── 설정 ──────────────────────────────────────────────────────────────
LOGIN_URL  = "https://kis.okpos.co.kr/login/login_form.jsp"
PROD_URL   = "https://kis.okpos.co.kr/sale/sale/prod011.jsp"
USER_ID    = os.environ["KIS_ID"]
USER_PW    = os.environ["KIS_PW"]
BOT_TOKEN  = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID    = os.environ["TELEGRAM_CHAT_ID"]

# 관심 점포 (사이트 중분류명 그대로)
STORE_LABELS = {
      "매표소":      "🎟 입장객",
      "카페테리아":  "☕ 카페테리아",
      "레스토랑":    "🍜 레스토랑",
      "레스토랑신규":"🍽 레스토랑(신규)",
      "열린매대":    "🛒 열린매대",
      "무인점포":    "🤖 무인점포",
      "먹이판매":    "🐟 먹이판매",
      "드론체험":    "🚁 드론체험",
      "장난감":      "🧸 장난감",
}

# ── 날짜 계산 ──────────────────────────────────────────────────────────
def get_date_ranges(today: date):
      tf = today.strftime
      d_range  = (tf("%Y-%m-%d"), tf("%Y-%m-%d"))
      m_range  = (today.replace(day=1).strftime("%Y-%m-%d"), tf("%Y-%m-%d"))
      y_range  = (today.replace(month=1, day=1).strftime("%Y-%m-%d"), tf("%Y-%m-%d"))

    prev = today.replace(year=today.year - 1)
    pf = prev.strftime
    pd_range = (pf("%Y-%m-%d"), pf("%Y-%m-%d"))
    pm_range = (prev.replace(day=1).strftime("%Y-%m-%d"), pf("%Y-%m-%d"))
    py_range = (prev.replace(month=1, day=1).strftime("%Y-%m-%d"), pf("%Y-%m-%d"))

    return (d_range, m_range, y_range), (pd_range, pm_range, py_range)

# ── IBSheet XML 파싱 ───────────────────────────────────────────────────
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
                                                                        qty:      parseInt(row.getAttribute('C13') || '0'),
                                                                                    revenue:  parseInt(row.getAttribute('C15') || '0'),
                                                                                                net:      parseInt(row.getAttribute('C17') || '0'),
                                                                                                        };
                                                                                                            });
                                                                                                            
                                                                                                                // 합계 행 텍스트에서 총계 추출
                                                                                                                    const bodyText = document.body.innerText;
                                                                                                                        const lines = bodyText.split('\\n').filter(l => l.includes('합계'));
                                                                                                                            if (lines.length) {
                                                                                                                                    const nums = lines[0].match(/[\\d,]+/g);
                                                                                                                                            if (nums && nums.length >= 4) {
                                                                                                                                                        result['__total__'] = {
                                                                                                                                                                        qty:     parseInt(nums[0].replace(/,/g,'')),
                                                                                                                                                                                        revenue: parseInt(nums[2].replace(/,/g,'')),
                                                                                                                                                                                                        net:     parseInt(nums[3].replace(/,/g,'')),
                                                                                                                                                                                                                    };
                                                                                                                                                                                                                            }
                                                                                                                                                                                                                                }
                                                                                                                                                                                                                                    return result;
                                                                                                                                                                                                                                    }"""

# ── 데이터 조회 ────────────────────────────────────────────────────────
async def fetch(prod_frame, date_from: str, date_to: str) -> dict:
      await prod_frame.fill("#date1_1", date_from)
      await prod_frame.fill("#date1_2", date_to)
      await prod_frame.click("#date_period1")          # 기간 입력 확정
    await prod_frame.evaluate(
              "() => { document.getElementById('date1_2').value = arguments[0]; }",
              date_to
    )
    # 조회 버튼
    await prod_frame.evaluate("() => fnSearch()")
    await prod_frame.wait_for_timeout(4000)
    return await prod_frame.evaluate(PARSE_JS) or {}

# ── 메시지 포맷 ────────────────────────────────────────────────────────
def fmt(n: int) -> str:
      return f"{n:,}"

def growth(cur: int, prev: int) -> str:
      if prev == 0:
                return "(전년 데이터 없음)"
            pct = (cur - prev) / prev * 100
    arrow = "▲" if pct >= 0 else "▼"
    return f"{arrow}{abs(pct):.1f}%"

def section(title: str, data: dict, prev: dict) -> str:
      lines = [f"*{title}*"]
    total_net = 0
    for store_key, label in STORE_LABELS.items():
              d = data.get(store_key, {})
              qty = d.get("qty", 0)
              net = d.get("net", 0)
              if qty == 0 and net == 0:
                            continue
                        total_net += net
        p = prev.get(store_key, {})
        g = growth(net, p.get("net", 0))
        lines.append(f"  {label}: {fmt(qty)}건  {fmt(net)}원  {g}")

    # 합계
    total = data.get("__total__", {})
    t_net = total.get("net", total_net)
    p_total = prev.get("__total__", {})
    g_total = growth(t_net, p_total.get("net", 0))
    lines.append(f"  💰 *총 실매출: {fmt(t_net)}원  {g_total}*")
    return "\n".join(lines)

def build_message(today: date, daily, monthly, yearly, pd, pm, py) -> str:
      today_str = today.strftime("%Y년 %m월 %d일 (%a)")
    msg = [
              f"🦁 *쥬쥬랜드 일일 실적 보고*",
              f"📅 {today_str}",
              "",
              section("📆 일별", daily, pd),
              "",
              section("📅 월누계", monthly, pm),
              "",
              section("📊 연누계", yearly, py),
    ]
    return "\n".join(msg)

# ── 메인 ──────────────────────────────────────────────────────────────
async def main():
      today = date.today()
    (d_range, m_range, y_range), (pd_range, pm_range, py_range) = get_date_ranges(today)

    async with async_playwright() as p:
              browser = await p.chromium.launch(headless=True)
        ctx     = await browser.new_context(locale="ko-KR")
        page    = await ctx.new_page()

        # 로그인
        await page.goto(LOGIN_URL, wait_until="networkidle")
        await page.fill("input[name='userId'], #userId, input[placeholder='아이디']", USER_ID)
        await page.fill("input[name='userPw'], #userPw, input[type='password']", USER_PW)
        await page.click("button:has-text('로그인'), input[value='로그인']")
        await page.wait_for_timeout(4000)

        # 비번 변경 팝업 닫기
        for frame in page.frames:
                      try:
                                        btn = await frame.query_selector("button:has-text('닫기')")
                                        if btn:
                                                              await btn.click()
                                                              await page.wait_for_timeout(1000)
                                                              break
                                                      except:
                                        pass

        # 상품별 메뉴로 이동 (메뉴 클릭)
        try:
                      top_frames = [f for f in page.frames if "top_frame" in f.url or "menuv" in f.url]
            for tf in top_frames:
                              try:
                                                    await tf.click("text=매출관리", timeout=3000)
                                                    await page.wait_for_timeout(500)
                                                    await tf.click("text=매출현황", timeout=3000)
                                                    await page.wait_for_timeout(500)
                                                    await tf.click("text=상품별", timeout=3000)
                                                    await page.wait_for_timeout(3000)
                                                    break
                                                except:
                    continue
except Exception as e:
            print(f"메뉴 클릭 오류: {e}")

        # prod011 프레임 찾기
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
                      raise Exception("prod011 프레임을 찾을 수 없습니다")

        print("✅ 상품별 화면 접속 성공")

        # 올해 데이터
        daily   = await fetch(prod_frame, *d_range)
        monthly = await fetch(prod_frame, *m_range)
        yearly  = await fetch(prod_frame, *y_range)

        # 전년 데이터
        prev_daily   = await fetch(prod_frame, *pd_range)
        prev_monthly = await fetch(prod_frame, *pm_range)
        prev_yearly  = await fetch(prod_frame, *py_range)

        await browser.close()

    # 메시지 생성
    message = build_message(today, daily, monthly, yearly, prev_daily, prev_monthly, prev_yearly)
    print(message)

    # 텔레그램 전송
    bot = telegram.Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")
    print("✅ 텔레그램 전송 완료!")

if __name__ == "__main__":
      asyncio.run(main())
