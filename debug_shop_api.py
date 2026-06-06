"""OKPOS menu.jsp 매장/분석 메뉴 항목 및 네비게이션 URL 추출"""
import os, re, requests, urllib3

urllib3.disable_warnings()
BASE_URL = "https://kis.okpos.co.kr"
USER_ID  = os.environ["KIS_ID"]
USER_PW  = os.environ["KIS_PW"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

def extract_token(html):
    for pat in [
        r"id='([0-9a-f-]{36})'\s+name='([0-9a-f-]{36})'\s+value='([0-9a-f-]{36})'",
        r'name="([0-9a-f-]{36})"[^>]*value="([0-9a-f-]{36})"',
        r'name="([0-9a-f-]{36})"[^>]*value="([^"]+)"',
        r"name='([0-9a-f-]{36})'[^>]*value='([^']+)'",
    ]:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            return (m.group(2), m.group(3)) if len(m.groups()) == 3 else (m.group(1), m.group(2))
    return None, None

def do_login():
    sess = requests.Session()
    sess.headers.update(HEADERS)
    r0 = sess.get(BASE_URL + "/login/login_form.jsp", verify=False, timeout=30)
    n, v = extract_token(r0.text)
    login_data = {"user_id": USER_ID, "user_pwd": USER_PW, "AutoFg": "W"}
    if n: login_data[n] = v
    r1 = sess.post(BASE_URL + "/login/login_check.jsp", data=login_data,
                   headers={"Referer": BASE_URL + "/login/login_form.jsp"}, verify=False, timeout=30)
    n, v = extract_token(r1.text)
    r2 = sess.post(BASE_URL + "/login/login_check_action.jsp",
                   data={"user_id": USER_ID, "user_pwd": USER_PW, "AutoFg": "W", n: v},
                   headers={"Referer": BASE_URL + "/login/login_check.jsp"}, verify=False, timeout=30)
    if "top_frame" not in r2.text:
        raise RuntimeError(f"Login failed: {r2.text[:200]}")
    sess.get(BASE_URL + "/login/top_frame.jsp", verify=False, timeout=30)
    print("Login OK")
    return sess


def main():
    sess = do_login()

    # ── 1. menu.jsp 전체 텍스트 수신 ────────────────────────────────────
    r_menu = sess.get(BASE_URL + "/login/menu.jsp",
                      headers={"Referer": BASE_URL + "/login/top_frame.jsp"}, verify=False, timeout=30)
    text = r_menu.content.decode("utf-8", errors="ignore")
    lines = text.splitlines()
    print(f"menu.jsp: {len(text):,}자, {len(lines):,}줄")

    # ── 2. '매장' '분석' 포함 줄 + 전후 5줄 컨텍스트 ────────────────────
    print("\n=== '매장' 또는 '분석' 포함 라인 컨텍스트 ===")
    printed = set()
    keywords = ["매장", "분석", "stat"]
    for i, line in enumerate(lines):
        if any(k in line for k in keywords):
            block = range(max(0, i-3), min(len(lines), i+5))
            if i not in printed:
                print(f"\n--- L{i+1}: {line.strip()[:120]} ---")
                for j in block:
                    printed.add(j)
                    print(f"  {lines[j].rstrip()[:180]}")

    # ── 3. 모든 onclick 핸들러 ───────────────────────────────────────────
    print("\n=== onclick 핸들러 전체 ===")
    for m in re.finditer(r'onclick\s*=\s*["\']([^"\']{5,})["\']', text, re.IGNORECASE):
        fn = m.group(1).strip()
        print(f"  {fn[:200]}")

    # ── 4. menu.jsp가 로드하는 스크립트 파일 ─────────────────────────────
    print("\n=== 로드된 외부 스크립트 ===")
    for m in re.finditer(r'<script[^>]+src\s*=\s*["\']([^"\']+)["\']', text, re.IGNORECASE):
        src = m.group(1)
        print(f"  {src}")
        # 매장/매출분석 관련 스크립트면 내용도 확인
        if any(k in src.lower() for k in ["menu", "nav", "cswm"]):
            r = sess.get(BASE_URL + src if src.startswith("/") else src,
                         headers={"Referer": BASE_URL + "/login/menu.jsp"}, verify=False, timeout=15)
            content = r.content.decode("utf-8", errors="ignore")
            print(f"    크기={len(content):,}자")
            # 네비게이션 URL 패턴 찾기
            for nav in re.findall(r'["\'](?:/[a-zA-Z0-9/_\-]+\.jsp)["\']', content):
                if nav not in ['"/login/menu.jsp"', "'/login/menu.jsp'"]:
                    print(f"    JSP: {nav}")

    # ── 5. JSP 경로 후보 직접 시도 (Referer 포함) ───────────────────────
    print("\n=== JSP 경로 직접 시도 (Referer 포함) ===")
    candidates = [
        "/sale/stat/shop010.jsp",
        "/sale/stat/shopStat010.jsp",
        "/sale/stat/saleShop010.jsp",
        "/sale/sale/shopSale010.jsp",
        "/sale/sale/saleShop010.jsp",
        "/sale/month/shop010.jsp",
        "/sale/month/shopMonth010.jsp",
        "/stat/shop010.jsp",
        "/stat/sale/shop010.jsp",
        "/sale/stat/stat010.jsp",
        "/sale/sale/stat010.jsp",
        "/sale/sale/shopInfo010.jsp",
        "/info/shop/shop010.jsp",
        "/basic/shop/shop010.jsp",
    ]
    for path in candidates:
        r = sess.get(BASE_URL + path,
                     headers={"Referer": BASE_URL + "/login/menu.jsp"}, verify=False, timeout=10)
        status = r.status_code
        size = len(r.text)
        sym = "✅" if status == 200 else ("⚠️" if status == 302 else "❌")
        print(f"  {sym} [{status} {size:5}] {path}")
        if status == 200 and size > 500:
            # 유의미한 페이지면 제목과 form action 출력
            title = re.search(r'<title[^>]*>([^<]+)</title>', r.text, re.IGNORECASE)
            forms = re.findall(r'action\s*=\s*["\']([^"\']+)["\']', r.text)
            if title:
                print(f"    title: {title.group(1).strip()}")
            for f in forms:
                print(f"    form action: {f}")


if __name__ == "__main__":
    main()
