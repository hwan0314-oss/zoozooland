"""OKPOS HistoryFrm.AddTab 함수 정의 및 탭ID→URL 매핑 탐색"""
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


def check(sess, path, label, referer=None):
    hdrs = {"Referer": BASE_URL + (referer or "/login/top_frame.jsp")}
    r = sess.get(BASE_URL + path, headers=hdrs, verify=False, timeout=10)
    size = len(r.text)
    print(f"  [{r.status_code} {size:6}] {label}: {path}")
    return r if r.status_code == 200 and size > 200 else None


def main():
    sess = do_login()

    # ── 1. top_frame.jsp 구조 (frameset/frame/iframe 확인) ──────────────
    print("\n=== top_frame.jsp 구조 ===")
    r = sess.get(BASE_URL + "/login/top_frame.jsp",
                 headers={"Referer": BASE_URL + "/login/login_check_action.jsp"}, verify=False, timeout=30)
    text = r.content.decode("utf-8", errors="ignore")
    print(f"  크기: {len(text):,}자")
    # frame/iframe 태그 추출
    for m in re.finditer(r'<(?:frame|iframe)[^>]+>', text, re.IGNORECASE):
        print(f"  FRAME: {m.group()[:200]}")
    # HistoryFrm 참조
    for m in re.finditer(r'.{0,60}HistoryFrm.{0,60}', text):
        print(f"  HistoryFrm: {m.group().strip()[:160]}")
    # 외부 스크립트 목록
    scripts = re.findall(r'<script[^>]+src\s*=\s*["\']([^"\']+)["\']', text, re.IGNORECASE)
    print(f"  외부 스크립트: {scripts}")

    # ── 2. menu.jsp 외부 스크립트에서 AddTab 정의 탐색 ──────────────────
    print("\n=== menu.jsp 외부 스크립트 → AddTab 탐색 ===")
    r_menu = sess.get(BASE_URL + "/login/menu.jsp",
                      headers={"Referer": BASE_URL + "/login/top_frame.jsp"}, verify=False, timeout=30)
    menu_text = r_menu.content.decode("utf-8", errors="ignore")
    menu_scripts = re.findall(r'<script[^>]+src\s*=\s*["\']([^"\']+)["\']', menu_text, re.IGNORECASE)
    print(f"  메뉴 스크립트 목록: {menu_scripts}")

    for src in menu_scripts:
        url = BASE_URL + src if src.startswith("/") else src
        r = sess.get(url, headers={"Referer": BASE_URL + "/login/menu.jsp"}, verify=False, timeout=15)
        js = r.content.decode("utf-8", errors="ignore")
        print(f"\n  [{r.status_code} {len(js):,}자] {src}")
        if "AddTab" in js:
            # AddTab 함수 전체 출력
            m = re.search(r'.{0,30}AddTab.{0,2000}', js, re.DOTALL)
            if m:
                print(f"    AddTab 발견:\n{m.group()[:2000]}")
        if "000132" in js or "000323" in js:
            print(f"    탭ID 데이터 발견!")
            idx = js.find("000132")
            if idx < 0: idx = js.find("000323")
            print(f"    컨텍스트: ...{js[max(0,idx-200):idx+300]}...")

    # ── 3. HistoryFrm 관련 JSP 탐색 ─────────────────────────────────────
    print("\n=== HistoryFrm 관련 JSP 탐색 ===")
    candidates = [
        "/login/history.jsp",
        "/login/historyFrm.jsp",
        "/login/tab.jsp",
        "/login/tabFrm.jsp",
        "/login/menuTab.jsp",
        "/login/tabHistory.jsp",
        "/common/jsp/history.jsp",
        "/common/jsp/tab.jsp",
        "/login/main.jsp",
        "/login/content.jsp",
        "/login/mainFrm.jsp",
    ]
    for path in candidates:
        r = check(sess, path, "")
        if r:
            t = r.content.decode("utf-8", errors="ignore")
            if "AddTab" in t:
                print(f"    ★ AddTab 발견!")
                m = re.search(r'.{0,50}AddTab.{0,1000}', t, re.DOTALL)
                if m: print(f"    {m.group()[:800]}")
            frames = re.findall(r'<(?:frame|iframe)[^>]+>', t, re.IGNORECASE)
            for f in frames:
                print(f"    FRAME: {f[:150]}")

    # ── 4. 메뉴ID → URL 서버 조회 시도 ──────────────────────────────────
    print("\n=== 메뉴ID → URL 서버 조회 시도 ===")
    sample_ids = ["000132", "000323", "000111"]
    for menuId in sample_ids:
        url_patterns = [
            f"/login/getMenuUrl.jsp?menuId={menuId}",
            f"/login/getPagePath.jsp?menuId={menuId}",
            f"/login/menuDetail.jsp?menuId={menuId}",
            f"/common/getMenuUrl.jsp?menuId={menuId}",
            f"/login/menu_page.jsp?menuId={menuId}",
        ]
        for path in url_patterns:
            r = check(sess, path, f"menuId={menuId}")

    # ── 5. top_frame.jsp의 자식 프레임 재귀 탐색 ───────────────────────
    print("\n=== top_frame.jsp 내 프레임 재귀 조회 ===")
    frame_srcs = re.findall(r'<(?:frame|iframe)[^>]+src\s*=\s*["\']([^"\']+)["\']', text, re.IGNORECASE)
    for src in frame_srcs:
        url = BASE_URL + src if src.startswith("/") else src
        r2 = sess.get(url, headers={"Referer": BASE_URL + "/login/top_frame.jsp"}, verify=False, timeout=10)
        t2 = r2.content.decode("utf-8", errors="ignore")
        print(f"\n  [{r2.status_code} {len(t2):,}자] {src}")
        if "AddTab" in t2:
            print(f"    ★ AddTab 발견!")
            m = re.search(r'AddTab[^}]*\}', t2, re.DOTALL)
            if m: print(f"    {m.group()[:500]}")
        if "000132" in t2:
            idx = t2.find("000132")
            print(f"    탭ID 000132 발견: ...{t2[max(0,idx-100):idx+200]}...")
        # 이 프레임이 로드하는 스크립트
        sub_scripts = re.findall(r'<script[^>]+src\s*=\s*["\']([^"\']+)["\']', t2, re.IGNORECASE)
        for ss in sub_scripts[:5]:
            print(f"    sub-script: {ss}")


if __name__ == "__main__":
    main()
