"""OKPOS 매장별매출분석 sub-pages → S_CONTROLLER 추출 + API 호출"""
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


def try_api(sess, ctrl, n, v, date1, date2, api_path):
    payload = {
        n: v,
        "S_CONTROLLER": ctrl, "S_METHOD": "search",
        "SHEETSEQ": "1", "S_SAVENAME": "", "S_ORDERBY": "",
        "date1_1": date1, "date1_2": date2, "date_period1": "366",
        "ss_SHOP_CD": "", "ss_SHOP_NM": "전체",
        "ss_PAGE_SIZE": "50", "ss_PAGE_NO1": "1",
    }
    r = sess.post(BASE_URL + api_path, data=payload,
                  headers={"Referer": BASE_URL + "/sale/shopsale/shopsale010.jsp"},
                  verify=False, timeout=15)
    try:
        d = r.json()
        code = d.get("Result", {}).get("Code", 0)
        rows = len(d.get("Data", []))
        return code, rows, d
    except:
        return None, 0, {}


def main():
    today = date.today().strftime("%Y-%m-%d")
    jan1  = date.today().strftime("%Y") + "-01-01"
    sess  = do_login()

    base_ref = BASE_URL + "/sale/shopsale/shopsale010.jsp"

    # sub-pages: shopsale010.jsp 안의 탭들
    sub_pages = [
        ("dayranking010.jsp",   "매장순위"),
        ("dayranking020.jsp",   "매장순위(상품)"),
        ("monthranking010.jsp", "매장월별 순위"),
        ("type010.jsp",         "매장형태별 매출"),
        ("brand010.jsp",        "브랜드별 매출"),
    ]

    print("\n=== shopsale sub-pages S_CONTROLLER 탐색 ===")
    found_tokens = {}  # page → (n, v)
    found_ctrls  = {}  # page → ctrl

    for fname, label in sub_pages:
        path = f"/sale/shopsale/{fname}"
        r010 = sess.get(BASE_URL + path,
                        headers={"Referer": base_ref}, verify=False, timeout=15)
        t = r010.content.decode("utf-8", errors="ignore")
        print(f"\n[{r010.status_code} {len(t):5}] {path} ({label})")

        # S_CONTROLLER 직접 값 추출 (value= 패턴)
        ctrls = re.findall(r"S_CONTROLLER[^'\"]{0,5}['\"]([a-zA-Z0-9_.]+)['\"]", t)
        if ctrls:
            for c in ctrls:
                if '.' in c:
                    print(f"  → S_CONTROLLER 발견: {c}")
                    found_ctrls[fname] = c

        # CSRF 토큰
        n, v = extract_token(t)
        if n:
            found_tokens[fname] = (n, v)
            # 010 → 011 POST로 실제 폼 페이지 얻기
            fname_011 = fname.replace("010.jsp", "011.jsp")
            r011 = sess.post(BASE_URL + f"/sale/shopsale/{fname_011}",
                             data={n: v},
                             headers={"Referer": BASE_URL + path}, verify=False, timeout=15)
            t011 = r011.content.decode("utf-8", errors="ignore")
            print(f"  011.jsp: [{r011.status_code} {len(t011):5}]")
            if r011.status_code == 200 and len(t011) > 500:
                ctrls2 = re.findall(r"S_CONTROLLER[^'\"]{0,5}['\"]([a-zA-Z0-9_.]+)['\"]", t011)
                for c in ctrls2:
                    if '.' in c:
                        print(f"  → 011 S_CONTROLLER: {c}")
                        found_ctrls[fname] = c
                n2, v2 = extract_token(t011)
                if n2:
                    found_tokens[fname] = (n2, v2)

        # 주요 JS 변수/함수 패턴 출력 (잘라서)
        for kw in ["S_CONTROLLER", "ddd.htmlSheetAction", "SheetAction", "controller"]:
            for m in re.finditer(r'.{0,40}' + kw + r'.{0,80}', t, re.IGNORECASE):
                snippet = m.group().strip()
                if snippet not in ["", "."]:
                    print(f"  [{kw}] {snippet[:160]}")

    # ── API 호출: /sale/shopsale/ddd.htmlSheetAction ─────────────────────
    print("\n=== /sale/shopsale/ddd.htmlSheetAction 호출 ===")
    api_path = "/sale/shopsale/ddd.htmlSheetAction"

    # 모든 sub-page 토큰으로 가능한 컨트롤러 시도
    all_tokens = list(found_tokens.values())
    if not all_tokens:
        # fallback: prod 토큰
        r_p = sess.get(BASE_URL + "/sale/sale/prod010.jsp",
                       headers={"Referer": base_ref}, verify=False, timeout=15)
        n, v = extract_token(r_p.text)
        r_p2 = sess.post(BASE_URL + "/sale/sale/prod011.jsp", data={n: v},
                         verify=False, timeout=15)
        n2, v2 = extract_token(r_p2.text)
        all_tokens = [(n2, v2)]

    n_tok, v_tok = all_tokens[0]

    controllers = [
        # 발견된 컨트롤러
        *list(found_ctrls.values()),
        # 추측 컨트롤러
        "sale.shopsale.dayranking011",
        "sale.shopsale.dayRanking011",
        "sale.shopsale.DayRanking011",
        "sale.shopsale.monthranking011",
        "sale.shopsale.type011",
        "sale.shopsale.brand011",
        "shopsale.dayranking011",
        "sale.dayranking011",
    ]
    # 중복 제거
    seen = set()
    controllers = [c for c in controllers if c not in seen and not seen.add(c)]

    for ctrl in controllers:
        code, rows, d = try_api(sess, ctrl, n_tok, v_tok, jan1, today, api_path)
        sym = "✅" if rows > 0 else ("⚠️" if code == 0 else "❌")
        print(f"  {sym} {ctrl}: code={code} rows={rows}")
        if rows > 0:
            print(f"    Keys: {list(d['Data'][0].keys())}")
            for row in d['Data'][:10]:
                print(f"    {json.dumps(row, ensure_ascii=False)[:150]}")

    # ── dayranking010.jsp 전체 출력 (S_CONTROLLER 못 찾으면) ─────────────
    if not any(rows > 0 for ctrl in controllers
               for code, rows, _ in [try_api(sess, ctrl, n_tok, v_tok, jan1, today, api_path)]):
        print("\n=== dayranking010.jsp 전체 내용 출력 ===")
        r = sess.get(BASE_URL + "/sale/shopsale/dayranking010.jsp",
                     headers={"Referer": base_ref}, verify=False, timeout=15)
        print(r.content.decode("utf-8", errors="ignore"))


if __name__ == "__main__":
    main()
