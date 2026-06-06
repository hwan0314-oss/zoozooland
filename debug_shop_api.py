"""OKPOS history.jsp / menuv.jsp 에서 '매장별매출분석' JSP 경로 추출"""
import os, re, json, requests, urllib3
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


def main():
    today = date.today().strftime("%Y-%m-%d")
    sess  = do_login()

    # ── 1. history.jsp → menu_arr 전체 파싱 ─────────────────────────────
    print("\n=== history.jsp menu_arr 파싱 ===")
    r = sess.get(BASE_URL + "/login/history.jsp",
                 headers={"Referer": BASE_URL + "/login/top_frame.jsp"}, verify=False, timeout=30)
    hist = r.content.decode("utf-8", errors="ignore")
    print(f"  크기: {len(hist):,}자")

    # menu_arr[N][K] = 'VALUE' 패턴으로 파싱
    entries = defaultdict(dict)
    for m in re.finditer(r"menu_arr\[(\d+)\]\[(\d+)\]\s*=\s*'([^']*)'", hist):
        i, k, v = int(m.group(1)), int(m.group(2)), m.group(3)
        entries[i][k] = v

    print(f"  총 메뉴 항목: {len(entries)}개")

    # 키 설명: [0]=대분류코드, [1]=대분류명, [2]=중분류코드, [3]=중분류명,
    #          [4]=프로그램코드, [5]=프로그램명, [6]=JSP경로, [7]=탭인덱스, [8]=즐겨찾기
    FIELDS = {0: "LCLS_CD", 1: "LCLS_NM", 2: "MCLS_CD", 3: "MCLS_NM",
              4: "PGM_CD", 5: "PGM_NM", 6: "PGM_FILE", 7: "TAB_IDX", 8: "FAV"}

    # 매출 관련 메뉴만 출력
    print("\n  [매출/분석/매장 관련 메뉴]")
    keywords = ["매출", "분석", "매장", "shop", "sale", "stat"]
    for i in sorted(entries.keys()):
        e = entries[i]
        pgm_nm = e.get(5, "")
        mcls_nm = e.get(3, "")
        lcls_nm = e.get(1, "")
        if any(k in pgm_nm for k in keywords) or any(k in mcls_nm for k in keywords):
            cd = e.get(4, "")
            path = e.get(6, "")
            print(f"  [{cd}] {lcls_nm} > {mcls_nm} > {pgm_nm}")
            print(f"        → {path}")

    # 매장별매출분석 직접 검색
    print("\n  ['매장별매출' 검색]")
    for i, e in entries.items():
        if "매장별" in e.get(5, "") or "매장별" in e.get(3, ""):
            print(f"  ★ 발견! [{e.get(4)}] {e.get(1)} > {e.get(3)} > {e.get(5)}")
            print(f"         JSP: {e.get(6)}")

    # ── 2. menuv.jsp → JSON 파싱 ─────────────────────────────────────────
    print("\n=== menuv.jsp JSON 파싱 ===")
    r2 = sess.get(BASE_URL + "/login/menuv.jsp",
                  headers={"Referer": BASE_URL + "/login/top_frame.jsp"}, verify=False, timeout=30)
    menuv = r2.content.decode("utf-8", errors="ignore")
    print(f"  크기: {len(menuv):,}자")

    # JSON 오브젝트 추출
    json_objects = re.findall(r'\{[^{}]+\}', menuv)
    parsed = []
    for obj in json_objects:
        try:
            d = json.loads(obj)
            if "PGM_NM" in d:
                parsed.append(d)
        except:
            pass
    print(f"  파싱된 메뉴 오브젝트: {len(parsed)}개")

    # 매장/매출 관련만 출력
    print("\n  [매출/분석/매장 관련 메뉴 (menuv.jsp)]")
    for d in parsed:
        nm = d.get("PGM_NM", "")
        mcls = d.get("PGM_MCLS_NM", "")
        if any(k in nm for k in keywords) or any(k in mcls for k in keywords):
            print(f"  [{d.get('PGM_CD')}] {d.get('PGM_LCLS_NM')} > {d.get('PGM_MCLS_NM')} > {nm}")
            print(f"        → {d.get('PGM_FILE_NM')}")

    # ── 3. 발견된 JSP로 API 탐색 ─────────────────────────────────────────
    print("\n=== 발견된 매장 관련 JSP 직접 접근 ===")
    # history.jsp에서 발견된 매장/매출 경로들 수집
    target_paths = set()
    for i, e in entries.items():
        nm = e.get(5, "")
        path = e.get(6, "")
        if path and ("매장" in nm or "분석" in nm or "shop" in path.lower() or "sale" in path.lower()):
            target_paths.add(path)

    for path in sorted(target_paths):
        r = sess.get(BASE_URL + path,
                     headers={"Referer": BASE_URL + "/login/top_frame.jsp"}, verify=False, timeout=10)
        print(f"  [{r.status_code} {len(r.text):5}] {path}")
        if r.status_code == 200 and len(r.text) > 500:
            t = r.content.decode("utf-8", errors="ignore")
            # S_CONTROLLER 값 찾기
            for m in re.finditer(r'S_CONTROLLER["\s:=\']+([a-zA-Z0-9_.]+)', t):
                print(f"    S_CONTROLLER: {m.group(1)}")
            # form action 찾기
            for m in re.finditer(r'action\s*=\s*["\']([^"\']+)["\']', t):
                print(f"    action: {m.group(1)}")
            title = re.search(r'<title[^>]*>([^<]+)</title>', t, re.IGNORECASE)
            if title:
                print(f"    title: {title.group(1).strip()}")

    # ── 4. 매장별매출분석 API 호출 (JSP 경로 발견 시) ─────────────────────
    # 발견된 경로 중 '매장별매출분석'에 해당하는 것을 바탕으로 API 호출
    shop_sale_path = None
    for i, e in entries.items():
        nm = e.get(5, "")
        if "매장별매출" in nm or ("매장" in nm and "분석" in nm):
            shop_sale_path = e.get(6, "")
            print(f"\n★★★ 매장별매출분석 발견: [{e.get(4)}] {nm}")
            print(f"    JSP: {shop_sale_path}")
            break

    if shop_sale_path:
        # 010.jsp → 011.jsp 패턴으로 API 접근
        api_path = shop_sale_path.replace("010.jsp", "011.jsp")
        print(f"\n=== 매장별매출분석 API 호출 시도 ===")
        r010 = sess.get(BASE_URL + shop_sale_path,
                        headers={"Referer": BASE_URL + "/login/top_frame.jsp"}, verify=False, timeout=15)
        print(f"  010.jsp: [{r010.status_code} {len(r010.text)}]")

        n, v = extract_token(r010.text)
        if n:
            r011 = sess.post(BASE_URL + api_path, data={n: v},
                             headers={"Referer": BASE_URL + shop_sale_path}, verify=False, timeout=15)
            print(f"  011.jsp: [{r011.status_code} {len(r011.text)}]")
            n2, v2 = extract_token(r011.text)

            # S_CONTROLLER 추출
            ctrl = None
            for m in re.finditer(r'S_CONTROLLER["\s:=\']+([a-zA-Z0-9_.]+)', r011.content.decode("utf-8", errors="ignore")):
                ctrl = m.group(1)
                print(f"  S_CONTROLLER 발견: {ctrl}")
                break

            if ctrl and n2:
                payload = {
                    n2: v2,
                    "S_CONTROLLER": ctrl, "S_METHOD": "search",
                    "SHEETSEQ": "1", "S_SAVENAME": "", "S_ORDERBY": "",
                    "date1_1": today, "date1_2": today, "date_period1": "366",
                    "ss_SHOP_CD": "", "ss_SHOP_NM": "전체",
                    "ss_PAGE_SIZE": "50", "ss_PAGE_NO1": "1",
                }
                r_api = sess.post(BASE_URL + "/sale/sale/ddd.htmlSheetAction", data=payload,
                                  headers={"Referer": BASE_URL + api_path}, verify=False, timeout=30)
                try:
                    d = r_api.json()
                    rows = d.get("Data", [])
                    code = d.get("Result", {}).get("Code", 0)
                    print(f"\n  API 결과: code={code}, rows={len(rows)}")
                    if rows:
                        print(f"  Keys: {list(rows[0].keys())}")
                        for row in rows[:10]:
                            print(f"  {json.dumps(row, ensure_ascii=False)[:150]}")
                except Exception as e:
                    print(f"  API 오류: {e}")
                    print(f"  응답: {r_api.text[:300]}")


if __name__ == "__main__":
    main()
