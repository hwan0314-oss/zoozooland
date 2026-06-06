"""
OKPOS 메뉴 구조 분석 + 매장별매출분석 API 탐색 v3
"""
import json, os, re, requests, urllib3
from datetime import date
from collections import defaultdict

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

def prod_api_call(sess, date_from, date_to):
    """기존 상품별 API 호출."""
    r1 = sess.get(BASE_URL + "/sale/sale/prod010.jsp",
                  headers={"Referer": BASE_URL + "/login/top_frame.jsp"}, verify=False, timeout=30)
    n, v = extract_token(r1.text)
    r2 = sess.post(BASE_URL + "/sale/sale/prod011.jsp", data={n: v},
                   headers={"Referer": BASE_URL + "/sale/sale/prod010.jsp"}, verify=False, timeout=30)
    n2, v2 = extract_token(r2.text)

    S_SAVENAME = (
        "sSeq|LCLS_NM|MCLS_NM|SCLS_NM|SALE_DATE|PROD_CD|BAR_CD|MAP_PROD_CD"
        "|PROD_NM|VENDORS_NM|COLOR_CD|SIZE_STR_CD|SALE_QTY|PROD_WEIGHT"
        "|TOT_SALE_AMT|TOT_DC_AMT|DCM_SALE_AMT|DC_AMT_GEN|DC_AMT_SVC"
        "|DC_AMT_JCD|DC_AMT_CPN|DC_AMT_CST|DC_AMT_FOD|DC_AMT_PACK"
        "|DC_AMT_YAP|SHOP_CD"
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
    return r.json().get("Data", [])

def main():
    today = date.today()
    fmt_d = lambda d: d.strftime("%Y-%m-%d")
    date_from = date_to = fmt_d(today)

    sess = do_login()

    # ── 1. menu.jsp 분석 ──────────────────────────────────────────────────────
    print("\n=== menu.jsp 분석 ===")
    r_menu = sess.get(BASE_URL + "/login/menu.jsp",
                      headers={"Referer": BASE_URL + "/login/top_frame.jsp"}, verify=False, timeout=30)
    menu_html = r_menu.text
    print(f"  menu.jsp len={len(menu_html)}")

    # JSP 경로 추출 (따옴표 안)
    all_jsps = sorted(set(re.findall(r"['\"](/[^'\"]+\.jsp[^'\"]*)['\"]", menu_html)))
    print(f"\n  전체 JSP 경로 ({len(all_jsps)}개):")
    for j in all_jsps:
        print(f"    {j}")

    # 매장/shop/store/sale 관련 키워드
    sale_related = [j for j in all_jsps if any(k in j.lower() for k in
                    ['sale', 'shop', 'store', 'stat', 'rpt', 'mgmt', 'anal'])]
    print(f"\n  sale 관련 JSP ({len(sale_related)}개):")
    for j in sale_related:
        print(f"    {j}")

    # 매장 관련 텍스트 컨텍스트
    print("\n  '매장' 키워드 컨텍스트:")
    for m in re.finditer(r'.{0,80}매장.{0,80}', menu_html):
        print(f"    {m.group().strip()}")

    # JavaScript 함수 호출 패턴
    print("\n  menuClick/goPage 패턴:")
    patterns = re.findall(r'(?:menuClick|goPage|location|href)\s*[=(]\s*["\']([^"\']+)["\']', menu_html)
    sale_patterns = [p for p in patterns if any(k in p.lower() for k in ['sale', 'shop', 'store'])]
    for p in sale_patterns[:20]:
        print(f"    {p}")

    # ── 2. 발견된 JSP 중 매장 관련 탐색 ──────────────────────────────────────
    if sale_related:
        print("\n=== sale-related JSP 직접 탐색 ===")
        for jsp in sale_related:
            try:
                r = sess.get(BASE_URL + jsp,
                             headers={"Referer": BASE_URL + "/login/menu.jsp"}, verify=False, timeout=10)
                ctrl = re.findall(r'S_CONTROLLER["\']?\s*[:=,]\s*["\']([^"\']+)["\']', r.text)
                n, v = extract_token(r.text)
                print(f"  [{r.status_code} {len(r.text):6d}] {jsp}  ctrl={ctrl[:2]}  token={'OK' if n else '-'}")
            except Exception as e:
                print(f"  [ERR] {jsp}: {e}")

    # ── 3. 매장별매출분석 컨트롤러 후보 직접 시도 ─────────────────────────────
    print("\n=== 매장별매출분석 컨트롤러 후보 시도 ===")
    r1 = sess.get(BASE_URL + "/sale/sale/prod010.jsp",
                  headers={"Referer": BASE_URL + "/login/top_frame.jsp"}, verify=False, timeout=30)
    n, v = extract_token(r1.text)
    r2 = sess.post(BASE_URL + "/sale/sale/prod011.jsp", data={n: v},
                   headers={"Referer": BASE_URL + "/sale/sale/prod010.jsp"}, verify=False, timeout=30)
    n2, v2 = extract_token(r2.text)

    ctrl_candidates = [
        "sale.sale.shop011", "sale.sale.shopSale011", "sale.sale.storeSale011",
        "sale.mgmt.shop011", "sale.stat.shop011", "sale.analysis.shop011",
        "sale.sale.saleShop011", "sale.sale.shopRpt011",
        "sale.rpt.shop011", "sale.rpt.shopSale011",
    ]

    for ctrl in ctrl_candidates:
        payload = {
            n2: v2,
            "S_CONTROLLER": ctrl, "S_METHOD": "search",
            "SHEETSEQ": "1", "S_SAVENAME": "", "S_ORDERBY": "",
            "date1_1": date_from, "date1_2": date_to,
            "date_period1": "366",
            "ss_SHOP_CD": "", "ss_SHOP_NM": "전체", "ss_SHOP_INFO": "[]",
            "ss_PAGE_SIZE": "100", "ss_PAGE_NO1": "1",
        }
        try:
            r = sess.post(BASE_URL + "/sale/sale/ddd.htmlSheetAction", data=payload,
                          headers={"Referer": BASE_URL + "/sale/sale/prod011.jsp"},
                          verify=False, timeout=20)
            data = r.json()
            code = data.get("Result", {}).get("Code", 0)
            msg = data.get("Result", {}).get("Message", "")[:50]
            rows = data.get("Data", [])
            status = "✅" if rows else ("⚠️" if code >= 0 else "❌")
            print(f"  {status} {ctrl}: code={code} rows={len(rows)} msg={msg}")
            if rows:
                print(f"     Keys: {list(rows[0].keys())}")
                for row in rows[:3]:
                    print(f"     {json.dumps(row, ensure_ascii=False)[:120]}")
        except Exception as e:
            print(f"  [ERR] {ctrl}: {e}")

    # ── 4. 오늘 전체 상품 데이터 MCLS_NM 상세 분석 ──────────────────────────
    print(f"\n=== 오늘({date_from}) 전체 매출 MCLS_NM 상세 ===")
    rows = prod_api_call(sess, date_from, date_to)
    print(f"  총 {len(rows)}개 행")

    # MCLS_NM별 상세 (SCLS_NM 포함)
    mcls_detail = defaultdict(lambda: defaultdict(lambda: {"qty": 0, "amt": 0}))
    for row in rows:
        mcls = row.get("MCLS_NM") or "?"
        scls = row.get("SCLS_NM") or "?"
        prod = row.get("PROD_NM") or "?"
        qty = int(row.get("SALE_QTY", 0) or 0)
        amt = int(row.get("DCM_SALE_AMT", 0) or 0)
        mcls_detail[mcls][f"{scls} | {prod}"]["qty"] += qty
        mcls_detail[mcls][f"{scls} | {prod}"]["amt"] += amt

    for mcls, detail in sorted(mcls_detail.items()):
        total_qty = sum(d["qty"] for d in detail.values())
        total_amt = sum(d["amt"] for d in detail.values())
        print(f"\n  [{mcls}] 합계: qty={total_qty}, amt={total_amt:,}원")
        for key, vals in sorted(detail.items(), key=lambda x: -x[1]["amt"]):
            print(f"    scls/prod: {key:<40s}  qty={vals['qty']:3d}  amt={vals['amt']:>10,}원")

    # ── 5. 입장매출 계산 검증 ─────────────────────────────────────────────────
    print(f"\n=== 입장매출 계산 (매표소 기준) ===")
    FREE_PRODUCTS = {"24개월미만무료입장", "초대권"}
    FOOD_KEYWORDS = ["먹이", "양분유체험"]
    ONLINE_TICKETS = {"온라인티켓(LS)", "네이버 주중", "네이버 주말"}

    adm_rev = {"individual": 0, "group": 0, "free": 0, "food": 0, "other": 0}
    adm_cnt = {"individual": 0, "group": 0, "free": 0}

    for row in rows:
        mcls = row.get("MCLS_NM") or ""
        prod_nm = (row.get("PROD_NM") or "").strip()
        scls_nm = (row.get("SCLS_NM") or "").strip()
        qty = int(row.get("SALE_QTY", 0) or 0)
        amt = int(row.get("DCM_SALE_AMT", 0) or 0)

        if mcls == "매표소":
            if prod_nm in FREE_PRODUCTS:
                adm_rev["free"] += amt
                adm_cnt["free"] += qty
            elif any(kw in prod_nm for kw in FOOD_KEYWORDS):
                adm_rev["food"] += amt
            elif "단체" in scls_nm or "단체" in prod_nm:
                adm_rev["group"] += amt
                adm_cnt["group"] += qty
            elif prod_nm in ONLINE_TICKETS:
                # 온라인 = 0원, 수량만
                adm_cnt["individual"] += qty
            elif "개인" in scls_nm:
                adm_rev["individual"] += amt
                adm_cnt["individual"] += qty
            else:
                adm_rev["other"] += amt
                print(f"    [매표소 미분류] scls={scls_nm}, prod={prod_nm}, qty={qty}, amt={amt}")

    print(f"  개인 수량: {adm_cnt['individual']}, 개인 POS 매출: {adm_rev['individual']:,}원")
    print(f"  단체 수량: {adm_cnt['group']}, 단체 매출: {adm_rev['group']:,}원")
    print(f"  무료 수량: {adm_cnt['free']}")
    print(f"  먹이판매(매표소): {adm_rev['food']:,}원")
    print(f"  기타(분류불가): {adm_rev['other']:,}원")
    print(f"  입장 총매출(POS): {adm_rev['individual'] + adm_rev['group']:,}원")

    # 동물먹이 MCLS_NM 별도 합계
    food_mcls = sum(int(r.get("DCM_SALE_AMT", 0) or 0) for r in rows if r.get("MCLS_NM") == "동물먹이")
    print(f"  먹이판매(동물먹이 MCLS): {food_mcls:,}원")

if __name__ == "__main__":
    main()
