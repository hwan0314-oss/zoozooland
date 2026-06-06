"""
OKPOS 매장별매출분석 API 탐색 스크립트
매출관리 > 매출분석 > 매장별매출분석 엔드포인트 및 응답 구조 확인
"""
import json
import os
import re
import requests
import urllib3
from datetime import date, timedelta

urllib3.disable_warnings()

BASE_URL = "https://kis.okpos.co.kr"
USER_ID  = os.environ["KIS_ID"]
USER_PW  = os.environ["KIS_PW"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
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
    if not n: raise RuntimeError("No CSRF token")
    r2 = sess.post(BASE_URL + "/login/login_check_action.jsp",
                   data={"user_id": USER_ID, "user_pwd": USER_PW, "AutoFg": "W", n: v},
                   headers={"Referer": BASE_URL + "/login/login_check.jsp"}, verify=False, timeout=30)
    if "top_frame" not in r2.text:
        raise RuntimeError(f"Login failed: {r2.text[:200]}")
    sess.get(BASE_URL + "/login/top_frame.jsp", verify=False, timeout=30)
    print("Login OK")
    return sess


def explore_menu(sess):
    """메인 메뉴에서 매장별매출분석 링크 탐색."""
    print("\n=== 메뉴 탐색 ===")
    # top_frame에서 메뉴 링크 수집
    r = sess.get(BASE_URL + "/login/top_frame.jsp", verify=False, timeout=30)
    links = re.findall(r'href=["\']([^"\']*shop[^"\']*)["\']', r.text, re.IGNORECASE)
    links += re.findall(r'href=["\']([^"\']*store[^"\']*)["\']', r.text, re.IGNORECASE)
    links += re.findall(r'href=["\']([^"\']*매장[^"\']*)["\']', r.text, re.IGNORECASE)
    print(f"  메뉴 링크(shop/store 관련): {links[:20]}")

    # 매출분석 계열 JSP 탐색
    candidates = [
        "/sale/sale/shop010.jsp",
        "/sale/sale/shop011.jsp",
        "/sale/analysis/shop010.jsp",
        "/sale/analysis/store010.jsp",
        "/sale/shop/shop010.jsp",
        "/sale/shop/shop011.jsp",
        "/sale/sale/shopSale010.jsp",
        "/sale/sale/shopSale011.jsp",
        "/sale/sale/storeSale010.jsp",
    ]
    print("\n=== JSP 경로 탐색 ===")
    for path in candidates:
        try:
            r = sess.get(BASE_URL + path, verify=False, timeout=10)
            tag = "[OK]" if r.status_code == 200 and len(r.text) > 200 else f"[{r.status_code}]"
            snippet = r.text[:120].replace('\n','').replace('\r','').strip() if r.status_code == 200 else ""
            print(f"  {tag} {path}  {snippet[:80]}")
        except Exception as e:
            print(f"  [ERR] {path}: {e}")


def get_api_token_for(sess, page_path):
    """지정 JSP 페이지에서 API 토큰 획득."""
    r1 = sess.get(BASE_URL + page_path,
                  headers={"Referer": BASE_URL + "/login/top_frame.jsp"}, verify=False, timeout=30)
    print(f"\n  {page_path}: {r1.status_code}, len={len(r1.text)}")
    if r1.status_code != 200 or len(r1.text) < 100:
        return None, None, r1.text[:300]

    # S_CONTROLLER 값 찾기
    ctrl = re.search(r"S_CONTROLLER['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", r1.text)
    print(f"  S_CONTROLLER: {ctrl.group(1) if ctrl else 'NOT FOUND'}")

    # 다음 JSP 링크
    next_jsp = re.search(r"action=['\"]([^'\"]+011[^'\"]*)['\"]", r1.text)
    print(f"  Next JSP: {next_jsp.group(1) if next_jsp else 'NOT FOUND'}")

    n, v = extract_token(r1.text)
    if not n:
        print("  No token found")
        return None, None, r1.text[:300]

    # 010 → 011 순서 탐색
    path011 = page_path.replace("010", "011")
    r2 = sess.post(BASE_URL + path011, data={n: v},
                   headers={"Referer": BASE_URL + page_path}, verify=False, timeout=30)
    print(f"  {path011}: {r2.status_code}, len={len(r2.text)}")

    ctrl2 = re.search(r"S_CONTROLLER['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", r2.text)
    n2, v2 = extract_token(r2.text)
    return n2, v2, r2.text[:500]


def try_store_api(sess, tok_name, tok_val, controller, date_from, date_to):
    """매장별매출분석 API 호출 시도."""
    API_URL = BASE_URL + "/sale/sale/ddd.htmlSheetAction"

    # 매장별 특화 S_SAVENAME 조합
    savenames = [
        "sSeq|SHOP_CD|SHOP_NM|TOT_SALE_AMT|TOT_DC_AMT|DCM_SALE_AMT|SALE_QTY",
        "SHOP_CD|SHOP_NM|SALE_AMT|DC_AMT|NET_AMT|SALE_CNT",
        "SHOP_CD|SHOP_NM|TOT_SALE_AMT|DCM_SALE_AMT",
        "",
    ]

    for sn in savenames:
        payload = {
            tok_name: tok_val,
            "S_CONTROLLER": controller, "S_METHOD": "search",
            "SHEETSEQ": "1", "S_SAVENAME": sn, "S_ORDERBY": "",
            "date1_1": date_from, "date1_2": date_to,
            "date_period1": "366",
            "ss_SHOP_CD": "", "ss_SHOP_NM": "전체", "ss_SHOP_INFO": "[]",
            "ss_PAGE_SIZE": "500", "ss_PAGE_NO1": "1",
        }
        r = sess.post(API_URL, data=payload,
                      headers={"Referer": BASE_URL + "/sale/sale/shop011.jsp"},
                      verify=False, timeout=30)
        print(f"\n  [API] controller={controller}, savename='{sn[:40]}'")
        print(f"    status={r.status_code}, len={len(r.text)}")
        try:
            data = r.json()
            result = data.get("Result", {})
            print(f"    Result.Code={result.get('Code')}, Msg={result.get('Message','')[:60]}")
            rows = data.get("Data", [])
            print(f"    Data rows: {len(rows)}")
            if rows:
                print(f"    First row keys: {list(rows[0].keys())}")
                print(f"    First row: {json.dumps(rows[0], ensure_ascii=False)[:200]}")
                return rows  # 성공
        except Exception as e:
            print(f"    JSON parse error: {e} | raw: {r.text[:100]}")
    return []


def main():
    today = date.today()
    fmt_d = lambda d: d.strftime("%Y-%m-%d")
    date_from = fmt_d(today)
    date_to   = fmt_d(today)

    sess = do_login()

    # 1) 메뉴에서 관련 링크 탐색
    explore_menu(sess)

    # 2) 알려진 패턴으로 JSP 직접 탐색
    shop_candidates = [
        "/sale/sale/shop010.jsp",
        "/sale/analysis/shop010.jsp",
        "/sale/shop/shop010.jsp",
    ]

    for page in shop_candidates:
        print(f"\n{'='*60}")
        print(f"탐색: {page}")
        n, v, html_snippet = get_api_token_for(sess, page)
        print(f"  HTML snippet: {html_snippet[:200]}")

        # controller 이름 추측
        for ctrl in [
            "sale.sale.shop011",
            "sale.analysis.shop011",
            "sale.shop.shop011",
            "sale.sale.shopSale011",
        ]:
            if n:
                rows = try_store_api(sess, n, v, ctrl, date_from, date_to)
                if rows:
                    print(f"\n✅ 성공! Controller: {ctrl}")
                    print(f"   전체 rows: {len(rows)}")
                    for row in rows[:5]:
                        print(f"   {json.dumps(row, ensure_ascii=False)}")
                    break

    # 3) 기존 상품별 API에서 SHOP_CD 기반으로 집계 가능한지 확인
    print(f"\n{'='*60}")
    print("기존 상품별 API 에서 SHOP_CD 확인")
    r1 = sess.get(BASE_URL + "/sale/sale/prod010.jsp",
                  headers={"Referer": BASE_URL + "/login/top_frame.jsp"}, verify=False, timeout=30)
    n, v = extract_token(r1.text)
    r2 = sess.post(BASE_URL + "/sale/sale/prod011.jsp", data={n: v},
                   headers={"Referer": BASE_URL + "/sale/sale/prod010.jsp"}, verify=False, timeout=30)
    n2, v2 = extract_token(r2.text)

    S_SAVENAME = (
        "sSeq|LCLS_NM|MCLS_NM|SCLS_NM|SALE_DATE|PROD_CD|PROD_NM"
        "|SALE_QTY|TOT_SALE_AMT|DCM_SALE_AMT|SHOP_CD|SHOP_NM"
    )
    payload = {
        n2: v2,
        "S_CONTROLLER": "sale.sale.prod011", "S_METHOD": "search",
        "SHEETSEQ": "1", "S_SAVENAME": S_SAVENAME, "S_ORDERBY": "",
        "ss_PROD_FG": "N", "date1_1": date_from, "date1_2": date_to,
        "date_period1": "366",
        "ss_PROD_CD": "", "ss_PROD_NM": "",
        "ss_LCLS_CD": "", "ss_MCLS_CD": "", "ss_SCLS_CD": "",
        "ss_CLS_TEXT": "전체", "ss_BAR_CD": "", "ss_SHOP_CD": "",
        "ss_SHOP_NM": "전체", "ss_SHOP_INFO": "[]",
        "ss_VENDOR_CD": "", "ss_VENDOR_NM": "전체", "ss_VENDOR_INFO": "[]",
        "ss_chk": "0", "ss_PAGE_SIZE": "500", "ss_PAGE_NO1": "1",
    }
    r = sess.post(BASE_URL + "/sale/sale/ddd.htmlSheetAction", data=payload,
                  headers={"Referer": BASE_URL + "/sale/sale/prod011.jsp"},
                  verify=False, timeout=60)
    data = r.json()
    rows = data.get("Data", [])
    print(f"  상품별 rows: {len(rows)}")

    # SHOP_NM별 합계
    shop_sums = {}
    for row in rows:
        shop = row.get("SHOP_NM") or row.get("SHOP_CD") or "?"
        amt  = int(row.get("DCM_SALE_AMT", 0) or row.get("TOT_SALE_AMT", 0) or 0)
        shop_sums[shop] = shop_sums.get(shop, 0) + amt
    print("\n  SHOP_NM별 합계 (상품별 API):")
    for shop, amt in sorted(shop_sums.items(), key=lambda x: -x[1]):
        print(f"    {shop:20s} {amt:>12,}원")

    if rows:
        print(f"\n  Sample row keys: {list(rows[0].keys())}")


if __name__ == "__main__":
    main()
