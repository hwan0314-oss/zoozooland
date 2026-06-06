"""OKPOS shopsale010.jsp 내용 분석 + 매장별매출분석 API 호출"""
import os, re, json, requests, urllib3
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


def main():
    today = date.today().strftime("%Y-%m-%d")
    jan1  = date.today().strftime("%Y") + "-01-01"
    sess  = do_login()

    # ── 1. shopsale010.jsp 전체 내용 출력 ───────────────────────────────
    print("\n=== shopsale010.jsp 전체 내용 ===")
    r010 = sess.get(BASE_URL + "/sale/shopsale/shopsale010.jsp",
                    headers={"Referer": BASE_URL + "/login/top_frame.jsp"}, verify=False, timeout=15)
    content = r010.content.decode("utf-8", errors="ignore")
    print(content)

    # ── 2. shopsale 관련 JSP 변형 시도 ─────────────────────────────────
    print("\n=== shopsale 관련 JSP 변형 시도 ===")
    paths = [
        "/sale/shopsale/shopsale020.jsp",
        "/sale/shopsale/shopsale_result.jsp",
        "/sale/shopsale/shopsale_search.jsp",
        "/sale/shopsale/shopsaleList.jsp",
        "/sale/shopsale/shopsale011.jsp",
        "/sale/shopsale/list.jsp",
    ]
    for path in paths:
        r = sess.get(BASE_URL + path,
                     headers={"Referer": BASE_URL + "/sale/shopsale/shopsale010.jsp"}, verify=False, timeout=10)
        sym = "✅" if r.status_code == 200 else "❌"
        print(f"  {sym} [{r.status_code} {len(r.text):5}] {path}")
        if r.status_code == 200 and len(r.text) > 500:
            t = r.content.decode("utf-8", errors="ignore")
            for m in re.finditer(r'S_CONTROLLER["\s:=\']+([a-zA-Z0-9_.]+)', t):
                print(f"    S_CONTROLLER: {m.group(1)}")

    # ── 3. S_CONTROLLER 직접 추측 + API 호출 ───────────────────────────
    print("\n=== S_CONTROLLER 직접 추측 + API 호출 ===")
    # 먼저 prod011.jsp에서 CSRF 토큰 확보
    r_prod = sess.get(BASE_URL + "/sale/sale/prod010.jsp",
                      headers={"Referer": BASE_URL + "/login/top_frame.jsp"}, verify=False, timeout=15)
    n, v = extract_token(r_prod.text)
    r_prod2 = sess.post(BASE_URL + "/sale/sale/prod011.jsp", data={n: v},
                        headers={"Referer": BASE_URL + "/sale/sale/prod010.jsp"}, verify=False, timeout=15)
    n2, v2 = extract_token(r_prod2.text)

    controllers = [
        "sale.shopsale.shopsale011",
        "sale.shopsale.shopSale011",
        "sale.sale.shopsale011",
        "sale.sale.shopSale011",
        "sale.analysis.shopsale011",
        "sale.stat.shopsale011",
    ]
    for ctrl in controllers:
        payload = {
            n2: v2,
            "S_CONTROLLER": ctrl, "S_METHOD": "search",
            "SHEETSEQ": "1", "S_SAVENAME": "", "S_ORDERBY": "",
            "date1_1": jan1, "date1_2": today, "date_period1": "366",
            "ss_SHOP_CD": "", "ss_SHOP_NM": "전체",
            "ss_PAGE_SIZE": "50", "ss_PAGE_NO1": "1",
        }
        r = sess.post(BASE_URL + "/sale/sale/ddd.htmlSheetAction", data=payload,
                      headers={"Referer": BASE_URL + "/sale/shopsale/shopsale010.jsp"},
                      verify=False, timeout=15)
        try:
            d = r.json()
            code = d.get("Result", {}).get("Code", 0)
            rows = len(d.get("Data", []))
            sym = "✅" if rows > 0 else ("⚠️" if code >= 0 else "❌")
            print(f"  {sym} {ctrl}: code={code} rows={rows}")
            if rows > 0:
                print(f"    Keys: {list(d['Data'][0].keys())}")
                for row in d['Data'][:5]:
                    print(f"    {json.dumps(row, ensure_ascii=False)[:150]}")
        except Exception as e:
            print(f"  [ERR] {ctrl}: {e}")

    # ── 4. shopsale010.jsp가 로드하는 실제 API URL 탐색 ─────────────────
    # shopsale010.jsp가 iframe이나 다른 JSP를 로드하면 그 쪽 토큰으로 API 호출
    print("\n=== shopsale010.jsp POST 시도 ===")
    n3, v3 = extract_token(content)
    print(f"  토큰: n={n3}, v={v3[:20] if v3 else None}")

    # POST to shopsale010.jsp itself
    if n3:
        payload_010 = {
            n3: v3,
            "date1_1": jan1, "date1_2": today, "date_period1": "366",
            "ss_SHOP_CD": "", "ss_SHOP_NM": "전체",
            "ss_PAGE_SIZE": "50", "ss_PAGE_NO1": "1",
        }
        r_post = sess.post(BASE_URL + "/sale/shopsale/shopsale010.jsp", data=payload_010,
                           headers={"Referer": BASE_URL + "/sale/shopsale/shopsale010.jsp"},
                           verify=False, timeout=15)
        print(f"  POST 010: [{r_post.status_code} {len(r_post.text)}]")
        t = r_post.content.decode("utf-8", errors="ignore")
        # S_CONTROLLER 탐색
        for m in re.finditer(r'S_CONTROLLER["\s:=\']+([a-zA-Z0-9_.]+)', t):
            print(f"  S_CONTROLLER: {m.group(1)}")
        # 결과 데이터 시작 부분
        if "SHOP" in t or "매장" in t:
            for m in re.finditer(r'.{0,100}(?:SHOP|매장).{0,100}', t):
                print(f"  → {m.group()[:200]}")

    # ── 5. ddd.htmlSheetAction을 shopsale Referer로 시도 ────────────────
    print("\n=== ddd.htmlSheetAction shopsale Referer 시도 ===")
    # shopsale010.jsp → POST → shopsale가 내부적으로 쓰는 endpoint 탐색
    # shopsale010.jsp 내 form action 추출
    form_actions = re.findall(r'action\s*=\s*["\']([^"\']+)["\']', content, re.IGNORECASE)
    print(f"  form actions in shopsale010.jsp: {form_actions}")

    iframes = re.findall(r'src\s*=\s*["\']([^"\']+\.jsp[^"\']*)["\']', content, re.IGNORECASE)
    print(f"  iframe/src in shopsale010.jsp: {iframes}")

    # 다른 API endpoint도 시도
    api_paths = [
        "/sale/shopsale/ddd.htmlSheetAction",
        "/sale/shopsale/shopsale_api.jsp",
        "/sale/ddd.htmlSheetAction",
        "/ddd.htmlSheetAction",
    ]
    if n3 and v3:
        for api_path in api_paths:
            payload_api = {
                n3: v3,
                "S_CONTROLLER": "sale.shopsale.shopsale011", "S_METHOD": "search",
                "SHEETSEQ": "1", "S_SAVENAME": "", "S_ORDERBY": "",
                "date1_1": jan1, "date1_2": today,
                "ss_SHOP_CD": "", "ss_PAGE_SIZE": "50", "ss_PAGE_NO1": "1",
            }
            r = sess.post(BASE_URL + api_path, data=payload_api,
                          headers={"Referer": BASE_URL + "/sale/shopsale/shopsale010.jsp"},
                          verify=False, timeout=10)
            sym = "✅" if r.status_code == 200 else "❌"
            print(f"  {sym} [{r.status_code}] {api_path}: {r.text[:100]}")


if __name__ == "__main__":
    main()
