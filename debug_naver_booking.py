"""Naver 예약 파트너센터 - 이용완료 예약 현황 디버그
GitHub Secrets: NAVER_ID, NAVER_PW
"""
import asyncio
import json
import os
from datetime import date
from playwright.async_api import async_playwright

NAVER_ID = os.environ["NAVER_ID"]
NAVER_PW = os.environ["NAVER_PW"]
BIZ_ID   = "480021"


async def main():
    today    = date.today()
    date_str = today.strftime("%Y-%m-%d")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = await ctx.new_page()

        # ── API 응답 가로채기 ──────────────────────────────────────────────
        captured = []

        async def on_response(resp):
            url = resp.url
            if "partner-api" in url or ("booking" in url and "naver" in url):
                try:
                    body = await resp.json()
                    captured.append({"url": url, "status": resp.status, "body": body})
                    print(f"[API] {resp.status} {url}")
                except Exception:
                    pass

        page.on("response", on_response)

        # ── 1. 네이버 로그인 ──────────────────────────────────────────────
        print("=== 네이버 로그인 ===")
        await page.goto(
            "https://nid.naver.com/nidlogin.login?mode=form&url=https%3A%2F%2Fwww.naver.com"
        )
        await page.wait_for_load_state("domcontentloaded")
        await page.fill("#id", NAVER_ID)
        await page.fill("#pw", NAVER_PW)
        await page.click(".btn_login")
        await page.wait_for_timeout(4000)

        cur_url = page.url
        print(f"로그인 후 URL: {cur_url}")

        if "nidlogin" in cur_url or "nid.naver" in cur_url:
            print("⚠️  로그인 실패 또는 추가 인증 필요")
            html = await page.content()
            print(html[:1000])
            await browser.close()
            return
        print("✅ 로그인 성공")

        # ── 2. 예약 파트너센터 이동 ───────────────────────────────────────
        print(f"\n=== 예약 캘린더 ({date_str}) ===")
        target = f"https://partner.booking.naver.com/bizes/{BIZ_ID}/booking-calendar-view"
        await page.goto(target)
        await page.wait_for_timeout(6000)
        print(f"현재 URL: {page.url}")

        # ── 3. 가로챈 API 목록 출력 ──────────────────────────────────────
        print(f"\n=== 가로챈 API 호출 ({len(captured)}개) ===")
        for item in captured:
            print(f"\n[{item['status']}] {item['url']}")
            print(json.dumps(item["body"], ensure_ascii=False, indent=2)[:600])

        # ── 4. 직접 API 호출 (이용완료 예약 조회) ────────────────────────
        print("\n=== 직접 API 호출 테스트 ===")

        endpoints = [
            # 날짜 범위 + 이용완료
            f"/partner-api/bizes/{BIZ_ID}/bookings?startDateTime={date_str}T00:00:00&endDateTime={date_str}T23:59:59&bookingStatus=USED&page=1&size=100",
            # 날짜 범위 + 전체
            f"/partner-api/bizes/{BIZ_ID}/bookings?startDateTime={date_str}T00:00:00&endDateTime={date_str}T23:59:59&page=1&size=100",
            # 날짜만
            f"/partner-api/bizes/{BIZ_ID}/bookings?date={date_str}&bookingStatus=USED",
            # 통계
            f"/partner-api/bizes/{BIZ_ID}/booking-statistics?startDate={date_str}&endDate={date_str}",
            # 이용완료 목록 (다른 경로)
            f"/partner-api/bizes/{BIZ_ID}/used-bookings?startDate={date_str}&endDate={date_str}&page=1&size=100",
        ]

        for ep in endpoints:
            result = await page.evaluate(
                f"""
                async (url) => {{
                    try {{
                        const r = await fetch('https://partner.booking.naver.com' + url,
                            {{credentials: 'include', headers: {{'Accept': 'application/json'}}}});
                        return {{status: r.status, body: await r.text()}};
                    }} catch(e) {{
                        return {{status: -1, body: String(e)}};
                    }}
                }}
                """,
                ep,
            )
            print(f"\nEP: {ep[:80]}")
            print(f"Status: {result['status']}")
            body_str = result["body"]
            try:
                print(json.dumps(json.loads(body_str), ensure_ascii=False, indent=2)[:800])
            except Exception:
                print(body_str[:400])

        # ── 5. 쿠키 출력 (재사용을 위해) ─────────────────────────────────
        print("\n=== 인증 쿠키 ===")
        cookies = await ctx.cookies(["https://naver.com", "https://partner.booking.naver.com"])
        auth_keys = {"NID_AUT", "NID_SES", "NID_JKL"}
        for c in cookies:
            if c["name"] in auth_keys:
                print(f"{c['name']}={c['value'][:40]}...  (domain={c['domain']})")

        await browser.close()


asyncio.run(main())
