"""OKPOS 매장별매출분석 - 원시 응답 및 파라미터 진단"""
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

    jsp_path = "/sale/shopsale/dayranking010.jsp"
    r = sess.get(BASE_URL + jsp_path,
                 headers={"Referer": BASE_URL + "/sale/shopsale/shopsale010.jsp"},
                 verify=False, timeout=15)
    html = r.content.decode("utf-8", errors="ignore")
    n, v = extract_token(html)
    print(f"Token: {n} = {v}")

    # 시도할 파라미터 세트
    test_cases = [
        ("빈 S_SAVENAME + 연초~오늘", {
            "S_SAVENAME": "",
            "date1_1": jan1, "date1_2": today,
            "ss_SHOP_TYPE_FG": "%", "ss_SHOP_GROUP_CD": "%",
            "ss_TYPE_UD": "U", "ss_SEL_CNT": "500",
        }),
        ("빈 S_SAVENAME + 오늘만", {
            "S_SAVENAME": "",
            "date1_1": today, "date1_2": today,
            "ss_SHOP_TYPE_FG": "%", "ss_SHOP_GROUP_CD": "%",
            "ss_TYPE_UD": "U", "ss_SEL_CNT": "500",
        }),
        ("ss_SHOP_TYPE_FG 빈값", {
            "S_SAVENAME": "",
            "date1_1": jan1, "date1_2": today,
            "ss_SHOP_TYPE_FG": "", "ss_SHOP_GROUP_CD": "",
            "ss_TYPE_UD": "U", "ss_SEL_CNT": "500",
        }),
        ("하위 500", {
            "S_SAVENAME": "",
            "date1_1": jan1, "date1_2": today,
            "ss_SHOP_TYPE_FG": "%", "ss_SHOP_GROUP_CD": "%",
            "ss_TYPE_UD": "D", "ss_SEL_CNT": "500",
        }),
    ]

    for label, extra in test_cases:
        # 각 시도마다 토큰 재조회
        r2 = sess.get(BASE_URL + jsp_path,
                      headers={"Referer": BASE_URL + "/sale/shopsale/shopsale010.jsp"},
                      verify=False, timeout=15)
        html2 = r2.content.decode("utf-8", errors="ignore")
        n2, v2 = extract_token(html2)
        if not n2:
            print(f"\n[{label}] 토큰 없음")
            continue

        payload = {
            n2: v2,
            "S_CONTROLLER": "sale.shopsale.dayranking010",
            "S_METHOD": "search",
            "SHEETSEQ": "1",
            "S_ORDERBY": "",
            "date_period1": "366",
            "EX_CST": "false",
            **extra,
        }
        r3 = sess.post(BASE_URL + "/sale/shopsale/ddd.htmlSheetAction",
                       data=payload,
                       headers={"Referer": BASE_URL + jsp_path},
                       verify=False, timeout=15)
        try:
            d = r3.json()
            code = d.get("Result", {}).get("Code", "?")
            msg  = d.get("Result", {}).get("Msg", "")
            rows = len(d.get("Data", []))
            print(f"\n[{label}] code={code} rows={rows} msg={msg}")
            # 전체 Result 객체 출력
            print(f"  Result: {json.dumps(d.get('Result', {}), ensure_ascii=False)}")
            if rows > 0:
                print(f"  Keys: {list(d['Data'][0].keys())}")
                for row in d['Data'][:5]:
                    print(f"  {json.dumps(row, ensure_ascii=False)}")
            elif rows == 0:
                # 데이터 없을 때 전체 응답 구조 확인
                non_data_keys = {k: v for k, v in d.items() if k != 'Data'}
                print(f"  All keys: {list(d.keys())}")
                print(f"  Non-data: {json.dumps(non_data_keys, ensure_ascii=False)[:500]}")
        except Exception as e:
            print(f"\n[{label}] JSON 파싱 실패: {e}")
            print(f"  Raw (200자): {r3.text[:200]}")

    # ── 매장 목록 조회 시도 ──────────────────────────────────────────
    print("\n\n=== 매장 목록 직접 조회 ===")
    # prod API에서 SHOP_CD/SHOP_NM 조회 시도
    r_prod = sess.get(BASE_URL + "/sale/sale/prod010.jsp",
                      headers={"Referer": BASE_URL + "/sale/shopsale/shopsale010.jsp"},
                      verify=False, timeout=15)
    np, vp = extract_token(r_prod.content.decode("utf-8", errors="ignore"))
    if np:
        r_prod2 = sess.post(BASE_URL + "/sale/sale/prod011.jsp", data={np: vp},
                            verify=False, timeout=15)
        np2, vp2 = extract_token(r_prod2.content.decode("utf-8", errors="ignore"))
        if np2:
            shop_payload = {
                np2: vp2,
                "S_CONTROLLER": "sale.sale.prod011",
                "S_METHOD": "search",
                "SHEETSEQ": "1",
                "S_SAVENAME": "SHOP_CD,SHOP_NM,DCM_SALE_AMT,MCLS_NM,LCLS_NM",
                "S_ORDERBY": "",
                "date1_1": jan1, "date1_2": today,
                "date_period1": "366",
                "ss_SHOP_CD": "", "ss_SHOP_NM": "전체",
                "ss_PAGE_SIZE": "50", "ss_PAGE_NO1": "1",
            }
            r_shop = sess.post(BASE_URL + "/sale/sale/ddd.htmlSheetAction",
                               data=shop_payload, verify=False, timeout=15)
            try:
                d_shop = r_shop.json()
                rows_s = len(d_shop.get("Data", []))
                print(f"prod011 API: code={d_shop.get('Result',{}).get('Code')} rows={rows_s}")
                if rows_s > 0:
                    shops = set((row.get("SHOP_CD",""), row.get("SHOP_NM","")) for row in d_shop["Data"])
                    print(f"  매장목록: {sorted(shops)}")
                    mcls = set(row.get("MCLS_NM","") for row in d_shop["Data"])
                    print(f"  MCLS_NM: {sorted(mcls)}")
            except Exception as e:
                print(f"prod API 실패: {e}")

if __name__ == "__main__":
    main()
