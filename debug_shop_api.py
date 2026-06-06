"""
OKPOS 매장별매출분석 API 탐색 v1
- menu.jsp JavaScript에서 매장별 JSP 경로 추출
- shop010.jsp → shop011.jsp 흐름으로 올바른 CSRF 토큰 획득 시도
- 다양한 JSP 경로 후보 시도
"""
import json, os, re, requests, urllib3
from datetime import date

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


def try_api(sess, path010, referer, date_from, date_to, extra_payload=None):
    """010.jsp → 011.jsp → API 흐름으로 매장별 데이터 조회 시도."""
    path011 = path010.replace("010.jsp", "011.jsp")
    action  = BASE_URL + "/sale/sale/ddd.htmlSheetAction"

    # Step 1: 010 페이지
    r1 = sess.get(BASE_URL + path010,
                  headers={"Referer": BASE_URL + referer}, verify=False, timeout=20)
    if r1.status_code != 200:
        print(f"  [SKIP] {path010} → {r1.status_code}")
        return
    n1, v1 = extract_token(r1.text)
    ctrl_in_010 = re.findall(r'S_CONTROLLER["\']?\s*[:=,]\s*["\']([^"\']+)["\']', r1.text)
    print(f"  {path010}: {r1.status_code} len={len(r1.text)}  token={'OK' if n1 else '-'}  ctrl={ctrl_in_010[:2]}")

    # Step 2: 011 페이지
    post_data = {}
    if n1: post_data[n1] = v1
    r2 = sess.post(BASE_URL + path011, data=post_data,
                   headers={"Referer": BASE_URL + path010}, verify=False, timeout=20)
    if r2.status_code != 200:
        print(f"  [SKIP] {path011} → {r2.status_code}")
        return
    n2, v2 = extract_token(r2.text)
    ctrl_list = re.findall(r'S_CONTROLLER["\']?\s*[:=,]\s*["\']([^"\']+)["\']', r2.text)
    savename  = re.findall(r'S_SAVENAME["\']?\s*[:=,]\s*["\']([^"\']+)["\']', r2.text)
    print(f"  {path011}: {r2.status_code} len={len(r2.text)}  token={'OK' if n2 else '-'}  ctrl={ctrl_list[:3]}")
    if savename:
        print(f"    S_SAVENAME: {savename[0][:120]}")

    if not n2:
        # 토큰 없어도 ctrl이 있으면 시도
        if not ctrl_list:
            print("  [SKIP] no token and no controller")
            return

    # Step 3: API 호출
    for ctrl in (ctrl_list[:2] if ctrl_list else ["sale.sale.shop011"]):
        payload = {
            **(({n2: v2}) if n2 else {}),
            "S_CONTROLLER": ctrl, "S_METHOD": "search",
            "SHEETSEQ": "1",
            "S_SAVENAME": savename[0] if savename else "",
            "S_ORDERBY": "",
            "date1_1": date_from, "date1_2": date_to,
            "date_period1": "366",
            "ss_SHOP_CD": "", "ss_SHOP_NM": "전체", "ss_SHOP_INFO": "[]",
            "ss_CLS_TEXT": "전체",
            "ss_PAGE_SIZE": "100", "ss_PAGE_NO1": "1",
        }
        if extra_payload:
            payload.update(extra_payload)
        r3 = sess.post(action, data=payload,
                       headers={"Referer": BASE_URL + path011}, verify=False, timeout=20)
        try:
            data = r3.json()
        except Exception:
            print(f"    [{ctrl}] non-JSON response: {r3.text[:100]}")
            continue
        code = data.get("Result", {}).get("Code", 0)
        msg  = data.get("Result", {}).get("Message", "")[:60]
        rows = data.get("Data", [])
        status = "✅" if rows else ("⚠️" if code >= 0 else "❌")
        print(f"    {status} ctrl={ctrl}  code={code}  rows={len(rows)}  msg={msg}")
        if rows:
            print(f"      Keys: {list(rows[0].keys())}")
            for row in rows[:5]:
                print(f"      {json.dumps(row, ensure_ascii=False)[:160]}")


def main():
    today      = date.today().strftime("%Y-%m-%d")
    year_start = f"{date.today().year}-01-01"
    sess       = do_login()

    # ── 1. menu.jsp JavaScript 전체 파싱 ─────────────────────────────────────
    print("\n=== menu.jsp 심층 파싱 ===")
    r_menu = sess.get(BASE_URL + "/login/menu.jsp",
                      headers={"Referer": BASE_URL + "/login/top_frame.jsp"}, verify=False, timeout=30)
    menu_html = r_menu.text
    print(f"menu.jsp len={len(menu_html)}")

    # script 태그 내용 전체 추출
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', menu_html, re.DOTALL | re.IGNORECASE)
    all_script = '\n'.join(scripts)
    print(f"script content len={len(all_script)}")

    # 매장 관련 라인 전부 출력
    print("\n[매장/매출분석 관련 JavaScript 라인]")
    for line in all_script.split('\n'):
        stripped = line.strip()
        if not stripped:
            continue
        if any(k in stripped for k in ['매장', '매출분석', '분석', 'shop', 'Shop', 'SHOP']):
            print(f"  {stripped[:250]}")

    # 함수 호출 패턴 (어떤 함수명이든)
    print("\n[모든 함수 호출 패턴 - JSP 경로 포함]")
    func_calls = re.findall(r'\w+\s*\(\s*["\'][^"\']*(?:\.jsp|sale|shop|stat|rpt|anal)[^"\']*["\']', all_script)
    for fc in func_calls[:40]:
        print(f"  {fc[:200]}")

    # 모든 문자열 리터럴에서 경로 추출
    print("\n[스크립트 내 모든 경로형 문자열]")
    paths = sorted(set(re.findall(r"['\"]([/\w.-]+/[/\w.-]+\.jsp[^'\"]*)['\"]", all_script)))
    for p in paths:
        print(f"  {p}")

    # onclick, href 패턴에서 추출
    print("\n[onclick/href 매장 관련]")
    for m in re.finditer(r'(?:onclick|href)=["\'][^"\']*(?:매장|shop|sale\.sale)[^"\']*["\']', menu_html, re.IGNORECASE):
        print(f"  {m.group()[:200]}")

    # ── 2. 직접 JSP 경로 시도 (올바른 010→011 흐름) ──────────────────────────
    print("\n=== 매장별 JSP 경로 직접 시도 (올바른 010→011 흐름) ===")
    referer = "/login/top_frame.jsp"
    candidates_010 = [
        # shop 계열
        "/sale/sale/shop010.jsp",
        "/sale/sale/shop010.jsp",
        # sshop 계열 (store summary)
        "/sale/sale/sshop010.jsp",
        # shopRank 계열
        "/sale/sale/shopRank010.jsp",
        # stat 계열
        "/sale/stat/shop010.jsp",
        "/sale/stat/sshop010.jsp",
        # rpt 계열
        "/sale/rpt/shop010.jsp",
        # 매출분석 계열
        "/sale/sale/shopAnal010.jsp",
        "/sale/sale/shopSale010.jsp",
        "/sale/sale/shopStat010.jsp",
        # anal 계열
        "/sale/anal/shop010.jsp",
        # 한글 변수 시도
        "/sale/sale/maejang010.jsp",
        # prod011 기반 매장 컨트롤러 (prod 흐름 사용)
    ]
    for path010 in candidates_010:
        try_api(sess, path010, referer, today, today)

    # ── 3. prod011 토큰으로 더 많은 매장 컨트롤러 후보 시도 ──────────────────
    print("\n=== prod011 토큰으로 매장 컨트롤러 후보 시도 ===")
    r1 = sess.get(BASE_URL + "/sale/sale/prod010.jsp",
                  headers={"Referer": BASE_URL + "/login/top_frame.jsp"}, verify=False, timeout=30)
    n, v = extract_token(r1.text)
    r2 = sess.post(BASE_URL + "/sale/sale/prod011.jsp", data={n: v},
                   headers={"Referer": BASE_URL + "/sale/sale/prod010.jsp"}, verify=False, timeout=30)
    n2, v2 = extract_token(r2.text)

    ctrl_candidates = [
        # 기존 시도 (code=-9 반환했던 것들)
        "sale.sale.shop011",
        "sale.sale.shopSale011",
        "sale.stat.shop011",
        "sale.sale.sshop011",
        "sale.sale.shopRank011",
        "sale.sale.shopAnal011",
        "sale.sale.shopStat011",
        # 다른 패턴
        "sale.sale.store011",
        "sale.sale.pos011",
        "sale.sale.posShop011",
        "sale.rpt.shop011",
        "sale.anal.shop011",
        # 매출관리 계열
        "mgmt.sale.shop011",
        "sale.mgmt.shop011",
    ]

    action = BASE_URL + "/sale/sale/ddd.htmlSheetAction"
    for ctrl in ctrl_candidates:
        payload = {
            n2: v2,
            "S_CONTROLLER": ctrl, "S_METHOD": "search",
            "SHEETSEQ": "1", "S_SAVENAME": "", "S_ORDERBY": "",
            "date1_1": today, "date1_2": today, "date_period1": "366",
            "ss_SHOP_CD": "", "ss_SHOP_NM": "전체", "ss_SHOP_INFO": "[]",
            "ss_PAGE_SIZE": "100", "ss_PAGE_NO1": "1",
        }
        try:
            r = sess.post(action, data=payload,
                          headers={"Referer": BASE_URL + "/sale/sale/prod011.jsp"},
                          verify=False, timeout=15)
            data = r.json()
            code = data.get("Result", {}).get("Code", 0)
            msg  = data.get("Result", {}).get("Message", "")[:60]
            rows = data.get("Data", [])
            status = "✅" if rows else ("⚠️" if code >= 0 else "❌")
            print(f"  {status} {ctrl}: code={code} rows={len(rows)} msg={msg}")
            if rows:
                print(f"     Keys: {list(rows[0].keys())}")
                for row in rows[:3]:
                    print(f"     {json.dumps(row, ensure_ascii=False)[:160]}")
        except Exception as e:
            print(f"  [ERR] {ctrl}: {e}")

    # ── 4. top_frame.jsp 분석 (frame 구조 파악) ─────────────────────────────
    print("\n=== top_frame.jsp frame 구조 ===")
    r_top = sess.get(BASE_URL + "/login/top_frame.jsp",
                     headers={"Referer": BASE_URL + "/login/login_check_action.jsp"}, verify=False, timeout=30)
    print(r_top.text[:3000])


if __name__ == "__main__":
    main()
