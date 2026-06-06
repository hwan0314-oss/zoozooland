"""OKPOS 매장별매출분석 - 전체 매장 목록 출력"""
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

    # 토큰 취득
    r = sess.get(BASE_URL + jsp_path,
                 headers={"Referer": BASE_URL + "/sale/shopsale/shopsale010.jsp"},
                 verify=False, timeout=15)
    n, v = extract_token(r.content.decode("utf-8", errors="ignore"))

    payload = {
        n: v,
        "S_CONTROLLER": "sale.shopsale.dayranking010",
        "S_METHOD": "search",
        "SHEETSEQ": "1",
        "S_SAVENAME": "",
        "S_ORDERBY": "",
        "date1_1": jan1,
        "date1_2": today,
        "date_period1": "366",
        "ss_SHOP_TYPE_FG": "",   # ← 빈값이 핵심
        "ss_SHOP_GROUP_CD": "",  # ← 빈값이 핵심
        "ss_TYPE_UD": "U",
        "ss_SEL_CNT": "500",
        "EX_CST": "false",
    }
    r2 = sess.post(BASE_URL + "/sale/shopsale/ddd.htmlSheetAction",
                   data=payload,
                   headers={"Referer": BASE_URL + jsp_path},
                   verify=False, timeout=15)
    d = r2.json()
    rows = d.get("Data", [])
    print(f"\n=== 매장별 매출 ({jan1} ~ {today}) - 전체 {len(rows)}개 매장 ===")
    print(f"{'순위':>4}  {'매장명':<16}  {'실매출액(DCM)':>14}  {'영수건수':>8}  {'SHOP_CD'}")
    print("-" * 70)
    for i, row in enumerate(rows, 1):
        nm  = row.get("SHOP_NM", "")
        amt = int(row.get("DCM_SALE_AMT", 0))
        cnt = int(row.get("TOT_SALE_CNT", 0))
        cd  = row.get("SHOP_CD", "")
        print(f"{i:>4}  {nm:<16}  {amt:>14,}  {cnt:>8,}  {cd}")

    print(f"\n총계 SUM_SALE_AMT: {int(rows[0].get('SUM_SALE_AMT', 0)):,}" if rows else "")

if __name__ == "__main__":
    main()
