"""OKPOS SHOP_CD 집중 확인 + 매장 목록 API 탐색"""
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


def main():
    today = date.today().strftime("%Y-%m-%d")
    sess  = do_login()

    # ── 1. menu.jsp 인코딩 확인 + '매장' 검색 ────────────────────────────
    print("\n=== menu.jsp 인코딩 확인 ===")
    r_menu = sess.get(BASE_URL + "/login/menu.jsp",
                      headers={"Referer": BASE_URL + "/login/top_frame.jsp"}, verify=False, timeout=30)
    print(f"  HTTP 인코딩: {r_menu.encoding}")
    print(f"  Content-Type: {r_menu.headers.get('Content-Type')}")

    # EUC-KR 시도
    for enc in [r_menu.encoding or "utf-8", "euc-kr", "utf-8"]:
        try:
            text = r_menu.content.decode(enc, errors="ignore")
            cnt = text.count("매장")
            print(f"  [{enc}] '매장' 출현 횟수: {cnt}")
            if cnt > 0:
                idx = text.find("매장")
                print(f"  컨텍스트: ...{text[max(0,idx-80):idx+120]}...")
                break
        except Exception as e:
            print(f"  [{enc}] 디코딩 오류: {e}")

    # ── 2. prod010.jsp 에서 SHOP 관련 AJAX 패턴 ─────────────────────────
    print("\n=== prod010.jsp SHOP 관련 패턴 ===")
    r010 = sess.get(BASE_URL + "/sale/sale/prod010.jsp",
                    headers={"Referer": BASE_URL + "/login/top_frame.jsp"}, verify=False, timeout=30)
    for enc in [r010.encoding or "utf-8", "euc-kr"]:
        try:
            t010 = r010.content.decode(enc, errors="ignore")
            # SHOP 관련 라인
            for line in t010.split('\n'):
                if any(k in line for k in ['SHOP', 'shop', '매장', 'ss_SHOP']):
                    print(f"  {line.strip()[:200]}")
            break
        except:
            pass

    # ── 3. 상품별 API: SHOP_CD 실제 값 확인 ──────────────────────────────
    print("\n=== 상품별 API SHOP_CD 실제 값 ===")
    n, v = extract_token(r010.text)
    r011 = sess.post(BASE_URL + "/sale/sale/prod011.jsp", data={n: v},
                     headers={"Referer": BASE_URL + "/sale/sale/prod010.jsp"}, verify=False, timeout=30)
    n2, v2 = extract_token(r011.text)

    payload = {
        n2: v2,
        "S_CONTROLLER": "sale.sale.prod011", "S_METHOD": "search",
        "SHEETSEQ": "1",
        "S_SAVENAME": "LCLS_NM|MCLS_NM|PROD_NM|SALE_QTY|DCM_SALE_AMT|SHOP_CD|SHOP_NM",
        "S_ORDERBY": "",
        "ss_PROD_FG": "N", "date1_1": today, "date1_2": today, "date_period1": "366",
        "ss_PROD_CD": "", "ss_PROD_NM": "", "ss_LCLS_CD": "", "ss_MCLS_CD": "", "ss_SCLS_CD": "",
        "ss_CLS_TEXT": "전체", "ss_BAR_CD": "", "ss_SHOP_CD": "", "ss_SHOP_NM": "전체",
        "ss_SHOP_INFO": "[]", "ss_VENDOR_CD": "", "ss_VENDOR_NM": "전체", "ss_VENDOR_INFO": "[]",
        "ss_chk": "0", "ss_PAGE_SIZE": "300", "ss_PAGE_NO1": "1",
    }
    r = sess.post(BASE_URL + "/sale/sale/ddd.htmlSheetAction", data=payload,
                  headers={"Referer": BASE_URL + "/sale/sale/prod011.jsp"},
                  verify=False, timeout=60)
    rows = r.json().get("Data", [])
    print(f"총 {len(rows)}행 | 키: {list(rows[0].keys()) if rows else 'N/A'}")

    # 첫 5개 행 전체 출력 (SHOP_CD 값 확인)
    print("\n첫 5개 행 (전체 필드):")
    for row in rows[:5]:
        print(f"  {json.dumps(row, ensure_ascii=False)}")

    # SHOP_CD/SHOP_NM 분포
    shop_dist = defaultdict(lambda: {"cnt": 0, "amt": 0})
    for row in rows:
        cd = row.get("SHOP_CD") or ""
        nm = row.get("SHOP_NM") or ""
        key = f"CD={cd!r} NM={nm!r}"
        shop_dist[key]["cnt"] += 1
        shop_dist[key]["amt"] += int(row.get("DCM_SALE_AMT") or 0)

    print(f"\nSHOP_CD 분포 ({len(shop_dist)}종):")
    for key, v in sorted(shop_dist.items(), key=lambda x: -x[1]["amt"]):
        print(f"  {key}  건수={v['cnt']:3d}  매출={v['amt']:>12,}원")

    # ── 4. shop_group_type_tree.jsp 접근 (udfMainFrm.js에서 발견) ──────
    print("\n=== shop_group_type_tree.jsp 접근 시도 ===")
    paths = [
        "/common/jsp/shop_group_type_tree.jsp",
        "/common/jsp/shopList.jsp",
        "/common/jsp/shop_list.jsp",
    ]
    for path in paths:
        r = sess.get(BASE_URL + path,
                     headers={"Referer": BASE_URL + "/sale/sale/prod010.jsp"}, verify=False, timeout=10)
        print(f"  [{r.status_code} {len(r.text)}] {path}")
        if r.status_code == 200:
            # SHOP 관련 데이터 찾기
            for enc in [r.encoding or "utf-8", "euc-kr"]:
                try:
                    t = r.content.decode(enc, errors="ignore")
                    shops = re.findall(r'SHOP_CD[^"\']*["\']([^"\']+)["\']', t)
                    if shops:
                        print(f"    SHOP_CD 발견: {shops[:10]}")
                    # JSON 데이터 찾기
                    jsons = re.findall(r'\{[^{}]{10,200}\}', t)
                    for j in jsons[:3]:
                        if any(k in j for k in ['SHOP', 'shop', '매장']):
                            print(f"    JSON: {j[:200]}")
                    break
                except:
                    pass

    # ── 5. 매장 목록 전용 컨트롤러 시도 ────────────────────────────────
    print("\n=== 매장 목록 컨트롤러 탐색 ===")
    controllers = [
        "common.shop.shopList011",
        "basic.shop.shopList011",
        "sale.sale.shopList011",
        "login.shopInfo011",
        "common.common.shopList011",
        "sale.stat.shopStat011",
        "sale.sale.shopStat011",
        "sale.sale.saleShop011",
    ]
    for ctrl in controllers:
        payload2 = {
            n2: v2,
            "S_CONTROLLER": ctrl, "S_METHOD": "search",
            "SHEETSEQ": "1", "S_SAVENAME": "", "S_ORDERBY": "",
            "date1_1": today, "date1_2": today,
            "ss_SHOP_CD": "", "ss_SHOP_NM": "전체",
            "ss_PAGE_SIZE": "50", "ss_PAGE_NO1": "1",
        }
        try:
            r = sess.post(BASE_URL + "/sale/sale/ddd.htmlSheetAction", data=payload2,
                          verify=False, timeout=10)
            d = r.json()
            code = d.get("Result", {}).get("Code", 0)
            msg  = d.get("Result", {}).get("Message", "")[:40]
            rws  = len(d.get("Data", []))
            sym  = "✅" if rws > 0 else ("⚠️" if code >= 0 else "❌")
            print(f"  {sym} {ctrl}: code={code} rows={rws} msg={msg}")
            if rws > 0:
                print(f"    Keys: {list(d['Data'][0].keys())}")
                for row in d['Data'][:3]:
                    print(f"    {json.dumps(row, ensure_ascii=False)[:150]}")
        except Exception as e:
            print(f"  [ERR] {ctrl}: {e}")


if __name__ == "__main__":
    main()
