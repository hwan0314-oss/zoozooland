"""
OKPOS 매장별매출분석 API 탐색 스크립트 v2
- 내비게이션 프레임에서 실제 JSP URL 탐색
- 매출관리 > 매출분석 > 매장별매출분석 엔드포인트 확인
"""
import json
import os
import re
import requests
import urllib3
from datetime import date

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
    if n:
        login_data[n] = v
    r1 = sess.post(BASE_URL + "/login/login_check.jsp", data=login_data,
                   headers={"Referer": BASE_URL + "/login/login_form.jsp"}, verify=False, timeout=30)
    n, v = extract_token(r1.text)
    if not n:
        raise RuntimeError("No CSRF token")
    r2 = sess.post(BASE_URL + "/login/login_check_action.jsp",
                   data={"user_id": USER_ID, "user_pwd": USER_PW, "AutoFg": "W", n: v},
                   headers={"Referer": BASE_URL + "/login/login_check.jsp"}, verify=False, timeout=30)
    if "top_frame" not in r2.text:
        raise RuntimeError(f"Login failed: {r2.text[:200]}")
    r_top = sess.get(BASE_URL + "/login/top_frame.jsp", verify=False, timeout=30)
    print("Login OK")
    return sess, r_top.text


def probe(sess, path, ref="/login/top_frame.jsp"):
    """경로 probe 후 (status, len, text) 반환."""
    try:
        r = sess.get(BASE_URL + path, headers={"Referer": BASE_URL + ref}, verify=False, timeout=10)
        return r.status_code, len(r.text), r.text
    except Exception as e:
        return 0, 0, str(e)


def extract_jsps(html):
    """HTML/JS에서 .jsp 경로 추출."""
    paths = set(re.findall(r'["\']([^"\']*\.jsp[^"\']*)["\']', html))
    return sorted(p for p in paths if p.startswith('/') or p.startswith('http'))


def extract_controllers(html):
    """S_CONTROLLER 값 추출."""
    return re.findall(r'S_CONTROLLER["\']?\s*[:=,]\s*["\']([^"\']+)["\']', html)


def main():
    today = date.today()
    fmt_d = lambda d: d.strftime("%Y-%m-%d")
    date_from = fmt_d(today)
    date_to = fmt_d(today)

    sess, top_html = do_login()

    # ── 1. top_frame.jsp 분석 ─────────────────────────────────────────────────
    print("\n=== top_frame.jsp iframes / links ===")
    iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', top_html, re.IGNORECASE)
    print(f"  iframes: {iframes}")
    jsps_top = extract_jsps(top_html)
    sale_jsps = [j for j in jsps_top if 'sale' in j.lower() or 'stat' in j.lower()]
    print(f"  sale-related JSPs in top_frame: {sale_jsps[:20]}")
    ctrls = extract_controllers(top_html)
    print(f"  Controllers: {ctrls}")

    # ── 2. 프레임 탐색 ────────────────────────────────────────────────────────
    frame_candidates = [
        "/login/lnb.jsp", "/login/left.jsp", "/login/left_frame.jsp",
        "/login/menu.jsp", "/login/nav.jsp", "/login/navi.jsp",
        "/login/gnb.jsp",  "/login/main_frame.jsp", "/login/main.jsp",
    ]
    print("\n=== 프레임 탐색 ===")
    all_sale_jsps = set()
    for path in frame_candidates:
        status, length, text = probe(sess, path)
        if status == 200 and length > 200:
            jsps = extract_jsps(text)
            sale_found = [j for j in jsps if 'sale' in j.lower() or 'shop' in j.lower() or 'store' in j.lower()]
            print(f"  [OK {length:5d}] {path}: sale-jsps={sale_found[:8]}")
            all_sale_jsps.update(sale_found)
            ctrls = extract_controllers(text)
            if ctrls:
                print(f"           controllers: {ctrls[:5]}")
        else:
            print(f"  [{status}] {path}")

    # top_frame 내 모든 링크도 재확인
    all_links = re.findall(r'href=["\']([^"\']+)["\']', top_html, re.IGNORECASE)
    all_links += re.findall(r'src=["\']([^"\']+\.jsp[^"\']*)["\']', top_html, re.IGNORECASE)
    frame_urls = [l for l in all_links if l.startswith('/')]
    print(f"\n  top_frame 전체 링크: {frame_urls[:20]}")

    # ── 3. 발견된 JSP 직접 탐색 ──────────────────────────────────────────────
    if all_sale_jsps:
        print("\n=== 발견된 sale-JSP 탐색 ===")
        for jsp in sorted(all_sale_jsps):
            status, length, text = probe(sess, jsp)
            if status == 200 and length > 200:
                ctrls = extract_controllers(text)
                print(f"  [OK {length:5d}] {jsp}  ctrl={ctrls[:3]}")

    # ── 4. 브루트포스 탐색: 가능한 경로들 ────────────────────────────────────
    print("\n=== 브루트포스 경로 탐색 ===")
    brute_paths = []
    for prefix in ["/sale/sale/", "/sale/stat/", "/sale/rpt/", "/rpt/sale/",
                   "/mgmt/sale/", "/stat/sale/", "/sale/mgmt/"]:
        for name in ["shop010", "shopSale010", "storeSale010", "storeAnalysis010",
                     "saleshop010", "saleShop010", "shopAnalysis010",
                     "shop001", "shopStat010", "shopRpt010", "shopMgmt010",
                     "매장010", "store010", "sStore010", "shopList010"]:
            brute_paths.append(f"{prefix}{name}.jsp")

    for path in brute_paths:
        status, length, text = probe(sess, path)
        if status == 200 and length > 200:
            ctrls = extract_controllers(text)
            n, v = extract_token(text)
            print(f"  ✅ [OK {length:5d}] {path}  ctrl={ctrls}  token={'OK' if n else 'None'}")

    # ── 5. 상품별 API로 SHOP_CD, SHOP_NM 직접 요청 (필드 가용성 확인) ─────
    print("\n=== 상품별 API 필드 확인 ===")
    r1 = sess.get(BASE_URL + "/sale/sale/prod010.jsp",
                  headers={"Referer": BASE_URL + "/login/top_frame.jsp"}, verify=False, timeout=30)
    n, v = extract_token(r1.text)
    r2 = sess.post(BASE_URL + "/sale/sale/prod011.jsp", data={n: v},
                   headers={"Referer": BASE_URL + "/sale/sale/prod010.jsp"}, verify=False, timeout=30)
    n2, v2 = extract_token(r2.text)

    # 원본 S_SAVENAME에 SHOP_NM 추가
    S_SAVENAME = (
        "sSeq|LCLS_NM|MCLS_NM|SCLS_NM|SALE_DATE|PROD_CD|BAR_CD|MAP_PROD_CD"
        "|PROD_NM|VENDORS_NM|COLOR_CD|SIZE_STR_CD|SALE_QTY|PROD_WEIGHT"
        "|TOT_SALE_AMT|TOT_DC_AMT|DCM_SALE_AMT|DC_AMT_GEN|DC_AMT_SVC"
        "|DC_AMT_JCD|DC_AMT_CPN|DC_AMT_CST|DC_AMT_FOD|DC_AMT_PACK"
        "|DC_AMT_YAP|SHOP_CD|SHOP_NM"
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
    print(f"  총 rows: {len(rows)}")
    if rows:
        print(f"  Keys: {list(rows[0].keys())}")
        print(f"  Sample[0]: {json.dumps(rows[0], ensure_ascii=False)}")
        # SHOP_CD, SHOP_NM 있는지 확인
        has_shop_cd = any("SHOP_CD" in r for r in rows)
        has_shop_nm = any("SHOP_NM" in r for r in rows)
        print(f"  SHOP_CD 존재: {has_shop_cd}, SHOP_NM 존재: {has_shop_nm}")

        # MCLS_NM (매장 기준) 별 합계
        print("\n  MCLS_NM별 DCM_SALE_AMT 합계:")
        from collections import defaultdict
        mcls_sum = defaultdict(int)
        for row in rows:
            mcls = row.get("MCLS_NM") or "?"
            amt = int(row.get("DCM_SALE_AMT", 0) or 0)
            mcls_sum[mcls] += amt
        for k, v in sorted(mcls_sum.items(), key=lambda x: -x[1]):
            print(f"    {k:20s} {v:>12,}원")

        print("\n  LCLS_NM별 DCM_SALE_AMT 합계:")
        lcls_sum = defaultdict(int)
        for row in rows:
            lcls = row.get("LCLS_NM") or "?"
            amt = int(row.get("DCM_SALE_AMT", 0) or 0)
            lcls_sum[lcls] += amt
        for k, v in sorted(lcls_sum.items(), key=lambda x: -x[1]):
            print(f"    {k:20s} {v:>12,}원")


if __name__ == "__main__":
    main()
