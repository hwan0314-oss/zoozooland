"""
OKPOS 매장별매출분석 API 탐색 v2
- top_frame.js / udfMainFrm.js 에서 네비게이션 로직 추출
- menu.jsp 전체 HTML에서 매장 관련 데이터 구조 탐색
- 상품별 API 응답에서 SHOP_CD 실제 값 확인
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


def search_js(content, label, keywords):
    print(f"\n[{label}에서 키워드 검색]")
    found = False
    lines = content.split('\n')
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if any(k in stripped for k in keywords):
            # 전후 2줄 컨텍스트
            start = max(0, i-1)
            end   = min(len(lines), i+3)
            for j in range(start, end):
                print(f"  L{j+1}: {lines[j].strip()[:200]}")
            print()
            found = True
    if not found:
        print("  (없음)")


def main():
    today = date.today().strftime("%Y-%m-%d")
    sess  = do_login()

    # ── 1. 외부 JS 파일 읽기 ──────────────────────────────────────────────
    js_files = [
        "/login/top_frame.js",
        "/common/js/udfMainFrm.js",
    ]
    for path in js_files:
        r = sess.get(BASE_URL + path, verify=False, timeout=20)
        print(f"\n{'='*60}")
        print(f"=== {path}  [{r.status_code}  {len(r.text)}바이트] ===")
        print(f"{'='*60}")
        if r.status_code != 200:
            print("  접근 불가")
            continue

        content = r.text
        # 전체 출력 (최대 8000자)
        print(content[:8000])
        if len(content) > 8000:
            print(f"\n... (이하 {len(content)-8000}자 생략) ...\n")
            # 남은 부분에서 매장 관련만 추출
            search_js(content[8000:], "나머지 부분",
                      ['매장', 'shop', 'SHOP', 'sale', 'content', 'frame', 'src', 'load'])

    # ── 2. menu.jsp 전체 HTML에서 매장 관련 탐색 ─────────────────────────
    print(f"\n{'='*60}")
    print("=== menu.jsp 전체 HTML 매장 탐색 ===")
    r_menu = sess.get(BASE_URL + "/login/menu.jsp",
                      headers={"Referer": BASE_URL + "/login/top_frame.jsp"}, verify=False, timeout=30)
    menu_html = r_menu.text
    print(f"menu.jsp len={len(menu_html)}")

    # 매장 단어 주변 컨텍스트 출력
    print("\n[HTML에서 '매장' 단어 전후 200자]")
    for m in re.finditer(r'.{0,100}매장.{0,100}', menu_html):
        print(f"  ...{m.group().strip()[:250]}...")

    # data-* 속성 패턴 (현대 SPA에서 자주 사용)
    print("\n[data-* 속성 패턴]")
    data_attrs = re.findall(r'data-[\w-]+=[\"\'][^\"\']+[\"\']', menu_html)
    for attr in data_attrs[:30]:
        print(f"  {attr}")

    # 모든 onclick 속성 (첫 50개)
    print("\n[모든 onclick 속성 (처음 50개)]")
    onclicks = re.findall(r'onclick=["\'][^"\']{5,}["\']', menu_html)
    for oc in onclicks[:50]:
        print(f"  {oc[:200]}")

    # fnGoMenu / goMenu / goPage 패턴 전체
    print("\n[goMenu/goPage/fnGoMenu 패턴]")
    go_patterns = re.findall(r'(?:goMenu|goPage|fnGoMenu|fnMove|menuClick)\s*\([^)]+\)', menu_html)
    for p in go_patterns[:30]:
        print(f"  {p[:200]}")

    # JSON 배열/객체 패턴 (메뉴 데이터일 가능성)
    print("\n[큰 JSON 구조 시작 패턴 (100자 이상)]")
    json_chunks = re.findall(r'\[[\s\S]{100,500}?\]', menu_html)
    for chunk in json_chunks[:5]:
        print(f"  {chunk.strip()[:300]}")

    # ── 3. 상품별 API에서 SHOP_CD 실제 값 확인 ───────────────────────────
    print(f"\n{'='*60}")
    print("=== 상품별 API SHOP_CD 실제 값 확인 ===")
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
        "|DC_AMT_YAP|SHOP_CD|SHOP_NM"   # SHOP_NM도 추가
    )
    payload = {
        n2: v2,
        "S_CONTROLLER": "sale.sale.prod011", "S_METHOD": "search",
        "SHEETSEQ": "1", "S_SAVENAME": S_SAVENAME, "S_ORDERBY": "",
        "ss_PROD_FG": "N", "date1_1": today, "date1_2": today,
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
    rows = r.json().get("Data", [])
    print(f"총 {len(rows)}개 행, 첫 번째 행 키: {list(rows[0].keys()) if rows else 'N/A'}")

    # SHOP_CD / SHOP_NM 분포
    from collections import Counter
    shop_dist = Counter()
    for row in rows:
        cd = row.get("SHOP_CD") or "(empty)"
        nm = row.get("SHOP_NM") or "(empty)"
        shop_dist[(cd, nm)] += 1

    print(f"\nSHOP_CD / SHOP_NM 분포 ({len(shop_dist)}종):")
    for (cd, nm), cnt in sorted(shop_dist.items()):
        print(f"  SHOP_CD={cd!r}  SHOP_NM={nm!r}  건수={cnt}")

    # 샘플 원본 행 출력 (SHOP_CD 있는 것 우선)
    print("\n원본 행 샘플 (처음 10개, 전체 필드):")
    for row in rows[:10]:
        print(f"  {json.dumps(row, ensure_ascii=False)[:250]}")

    # ── 4. 추가: ss_SHOP_CD 파라미터로 특정 매장 필터링 가능한지 테스트 ──
    # 만약 SHOP_CD가 있다면, 특정 매장 코드로 필터링해볼 수 있음
    non_empty_shops = [(cd, nm) for (cd, nm), _ in shop_dist.items() if cd != "(empty)"]
    if non_empty_shops:
        print(f"\n✅ SHOP_CD가 존재합니다! 총 {len(non_empty_shops)}개 매장 코드")
        for cd, nm in non_empty_shops:
            cnt = shop_dist[(cd, nm)]
            total_amt = sum(int(r.get("DCM_SALE_AMT") or 0) for r in rows if (r.get("SHOP_CD") or "(empty)") == cd)
            print(f"  SHOP_CD={cd}  SHOP_NM={nm}  건수={cnt}  합계={total_amt:,}원")
    else:
        print("\n❌ 모든 행의 SHOP_CD가 비어있음 → 매장별 API 필요")


if __name__ == "__main__":
    main()
